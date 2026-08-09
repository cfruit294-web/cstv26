from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from config.asgi import application
from notifications.services import notify


def _access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class NotificationConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.token = _access_token_for(self.user)

    async def test_connect_without_token_is_rejected(self):
        communicator = WebsocketCommunicator(application, '/ws/notifications/')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_receives_realtime_push_on_notify(self):
        communicator = WebsocketCommunicator(application, f'/ws/notifications/?token={self.token}')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        from channels.db import database_sync_to_async

        await database_sync_to_async(notify)(self.user, 'Nouvelle commande', body='Détails', category='order')

        event = await communicator.receive_json_from()
        self.assertEqual(event['title'], 'Nouvelle commande')
        self.assertEqual(event['category'], 'order')

        await communicator.disconnect()
