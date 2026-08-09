"""Push temps réel des notifications d'un utilisateur, authentifié par JWT (?token=...)."""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4001)
            return

        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_event(self, event):
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'category': event['category'],
            'title': event['title'],
            'body': event['body'],
            'link': event['link'],
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
