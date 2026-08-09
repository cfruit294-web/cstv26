"""Chat temps réel d'un live via WebSocket, authentifié par JWT passé en query string (?token=...)."""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from live.models import LiveChatMessage, LiveStream

MAX_MESSAGE_LENGTH = 500


class LiveChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.group_name = f'live_chat_{self.stream_id}'

        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4001)
            return

        stream = await self._get_accessible_stream(self.stream_id, self.user)
        if stream is None:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message = (data.get('message') or '').strip()[:MAX_MESSAGE_LENGTH]
        if not message:
            return

        chat_message = await self._save_message(message)

        await self.channel_layer.group_send(self.group_name, {
            'type': 'chat.message',
            'user_email': self.user.email,
            'message': chat_message.message,
            'created_at': chat_message.created_at.isoformat(),
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'user_email': event['user_email'],
            'message': event['message'],
            'created_at': event['created_at'],
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
    def _get_accessible_stream(self, stream_id, user):
        stream = LiveStream.objects.filter(id=stream_id).first()
        if stream is None:
            return None
        if stream.owner_id == user.id or user.is_admin or stream.visibility == LiveStream.Visibility.PUBLIC:
            return stream
        return None

    @database_sync_to_async
    def _save_message(self, message):
        return LiveChatMessage.objects.create(stream_id=self.stream_id, user=self.user, message=message)
