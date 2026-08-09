from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from config.asgi import application
from live.models import LiveChatMessage, LiveStream


def _access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class LiveChatConsumerTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.public_stream = LiveStream.objects.create(owner=self.owner, title='Public', visibility=LiveStream.Visibility.PUBLIC)
        self.private_stream = LiveStream.objects.create(owner=self.owner, title='Private', visibility=LiveStream.Visibility.PRIVATE)
        # Générés en contexte synchrone : l'ORM refuse les écritures depuis un test async.
        self.owner_token = _access_token_for(self.owner)
        self.stranger_token = _access_token_for(self.stranger)

    async def test_connect_and_exchange_message_on_public_stream(self):
        token = self.stranger_token
        communicator = WebsocketCommunicator(application, f'/ws/live/{self.public_stream.id}/chat/?token={token}')

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data='{"message": "Bonjour tout le monde"}')
        response = await communicator.receive_json_from()

        self.assertEqual(response['message'], 'Bonjour tout le monde')
        self.assertEqual(response['user_email'], 'stranger@example.com')

        await communicator.disconnect()

        message_count = await self._count_messages(self.public_stream)
        self.assertEqual(message_count, 1)

    async def test_connect_without_token_is_rejected(self):
        communicator = WebsocketCommunicator(application, f'/ws/live/{self.public_stream.id}/chat/')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_connect_to_private_stream_as_stranger_is_rejected(self):
        token = self.stranger_token
        communicator = WebsocketCommunicator(application, f'/ws/live/{self.private_stream.id}/chat/?token={token}')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_owner_can_connect_to_private_stream(self):
        token = self.owner_token
        communicator = WebsocketCommunicator(application, f'/ws/live/{self.private_stream.id}/chat/?token={token}')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_two_clients_both_receive_broadcast_message(self):
        owner_comm = WebsocketCommunicator(
            application, f'/ws/live/{self.public_stream.id}/chat/?token={self.owner_token}',
        )
        stranger_comm = WebsocketCommunicator(
            application, f'/ws/live/{self.public_stream.id}/chat/?token={self.stranger_token}',
        )

        self.assertTrue((await owner_comm.connect())[0])
        self.assertTrue((await stranger_comm.connect())[0])

        await owner_comm.send_to(text_data='{"message": "Salut !"}')

        owner_echo = await owner_comm.receive_json_from()
        stranger_echo = await stranger_comm.receive_json_from()

        self.assertEqual(owner_echo['message'], 'Salut !')
        self.assertEqual(stranger_echo['message'], 'Salut !')

        await owner_comm.disconnect()
        await stranger_comm.disconnect()

    @staticmethod
    async def _count_messages(stream):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _count():
            return LiveChatMessage.objects.filter(stream=stream).count()

        return await _count()
