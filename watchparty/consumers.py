"""Salle de visionnage temps réel : chat + synchronisation de lecture (play/pause/seek).

Seuls l'hôte et les membres acceptés peuvent se connecter. Le contrôle de lecture (play/pause/seek)
est réservé à l'hôte et aux modérateurs ; les autres membres ne font que recevoir les événements de
synchronisation et discuter dans le chat.
"""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from watchparty.models import WatchParty, WatchPartyChatMessage, WatchPartyMembership

VALID_ACTIONS = {'play', 'pause', 'seek'}


class WatchPartyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.party_id = self.scope['url_route']['kwargs']['party_id']
        self.group_name = f'watchparty_{self.party_id}'

        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4001)
            return

        party = await self._get_party()
        if party is None:
            await self.close(code=4004)
            return

        if not await self._is_accepted_member(party):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'sync',
            'position': party.current_position_seconds,
            'is_playing': party.is_playing,
            'server_time': timezone.now().isoformat(),
        }))
        await self.channel_layer.group_send(self.group_name, {
            'type': 'presence.event', 'user_email': self.user.email, 'status': 'online',
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_send(self.group_name, {
                'type': 'presence.event', 'user_email': self.user.email, 'status': 'offline',
            })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'chat':
            content = (data.get('content') or '').strip()[:500]
            if not content:
                return
            message = await self._save_chat(content)
            await self.channel_layer.group_send(self.group_name, {
                'type': 'chat.message',
                'id': str(message.id),
                'user_email': self.user.email,
                'content': message.message,
                'created_at': message.created_at.isoformat(),
            })

        elif msg_type == 'playback':
            action = data.get('action')
            if action not in VALID_ACTIONS:
                return
            if not await self._can_moderate():
                return
            try:
                position = float(data.get('position', 0))
            except (TypeError, ValueError):
                return
            await self._update_playback(action, position)
            await self.channel_layer.group_send(self.group_name, {
                'type': 'playback.event',
                'action': action,
                'position': position,
                'is_playing': action != 'pause',
                'server_time': timezone.now().isoformat(),
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'id': event['id'],
            'user_email': event['user_email'],
            'content': event['content'],
            'created_at': event['created_at'],
        }))

    async def playback_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'playback',
            'action': event['action'],
            'position': event['position'],
            'is_playing': event['is_playing'],
            'server_time': event['server_time'],
        }))

    async def presence_event(self, event):
        if event['user_email'] != self.user.email:
            await self.send(text_data=json.dumps({
                'type': 'presence', 'user_email': event['user_email'], 'status': event['status'],
            }))

    async def _authenticate(self):
        query_string = self.scope['query_string'].decode()
        params = dict(pair.split('=', 1) for pair in query_string.split('&') if '=' in pair)
        token = params.get('token')
        if not token:
            return None
        try:
            access = AccessToken(token)
        except TokenError:
            return None
        return await self._get_user(access.get('user_id'))

    @database_sync_to_async
    def _get_user(self, user_id):
        return User.objects.filter(id=user_id).first()

    @database_sync_to_async
    def _get_party(self):
        return WatchParty.objects.filter(id=self.party_id).select_related('video').first()

    @database_sync_to_async
    def _is_accepted_member(self, party):
        return party.host_id == self.user.id or WatchPartyMembership.objects.filter(
            party=party, user=self.user, status=WatchPartyMembership.Status.ACCEPTED,
        ).exists()

    @database_sync_to_async
    def _can_moderate(self):
        party = WatchParty.objects.get(id=self.party_id)
        if party.host_id == self.user.id:
            return True
        return WatchPartyMembership.objects.filter(
            party=party, user=self.user, status=WatchPartyMembership.Status.ACCEPTED,
            role=WatchPartyMembership.Role.MODERATOR,
        ).exists()

    @database_sync_to_async
    def _save_chat(self, content):
        return WatchPartyChatMessage.objects.create(party_id=self.party_id, user=self.user, message=content)

    @database_sync_to_async
    def _update_playback(self, action, position):
        party = WatchParty.objects.get(id=self.party_id)
        party.playback_position_seconds = position
        party.is_playing = action != 'pause'
        party.playback_updated_at = timezone.now()
        party.save(update_fields=['playback_position_seconds', 'is_playing', 'playback_updated_at'])
