"""Messagerie temps réel via WebSocket : messages, indicateur de saisie, présence en ligne."""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from messaging.models import Conversation, Message


class ConversationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'conversation_{self.conversation_id}'

        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4001)
            return

        if not await self._is_participant(self.conversation_id, self.user):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
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

        if data.get('type') == 'typing':
            await self.channel_layer.group_send(self.group_name, {
                'type': 'typing.event', 'user_email': self.user.email,
            })
            return

        content = (data.get('content') or '').strip()
        if not content:
            return

        message = await self._save_message(content)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'chat.message',
            'id': str(message.id),
            'sender_email': self.user.email,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'sender_email': event['sender_email'],
            'content': event['content'],
            'created_at': event['created_at'],
        }))

    async def typing_event(self, event):
        if event['user_email'] != self.user.email:
            await self.send(text_data=json.dumps({'type': 'typing', 'user_email': event['user_email']}))

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
    def _is_participant(self, conversation_id, user):
        return Conversation.objects.filter(id=conversation_id, participants=user).exists()

    @database_sync_to_async
    def _save_message(self, content):
        message = Message.objects.create(conversation_id=self.conversation_id, sender=self.user, content=content)
        Conversation.objects.filter(id=self.conversation_id).update(updated_at=message.created_at)
        return message
