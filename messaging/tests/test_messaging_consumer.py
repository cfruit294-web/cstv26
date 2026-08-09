from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from config.asgi import application
from messaging.models import Conversation, Message


def _access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class ConversationConsumerTests(TransactionTestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', password='S3curePass!23')
        self.bob = User.objects.create_user(email='bob@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.conversation = Conversation.objects.create()
        self.conversation.participants.set([self.alice, self.bob])

        self.alice_token = _access_token_for(self.alice)
        self.bob_token = _access_token_for(self.bob)
        self.stranger_token = _access_token_for(self.stranger)

    async def test_participant_can_connect_and_send_message(self):
        communicator = WebsocketCommunicator(
            application, f'/ws/messaging/{self.conversation.id}/?token={self.alice_token}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data='{"content": "Salut Bob !"}')
        response = await communicator.receive_json_from()

        self.assertEqual(response['type'], 'message')
        self.assertEqual(response['content'], 'Salut Bob !')
        self.assertEqual(response['sender_email'], 'alice@example.com')

        await communicator.disconnect()

    async def test_non_participant_is_rejected(self):
        communicator = WebsocketCommunicator(
            application, f'/ws/messaging/{self.conversation.id}/?token={self.stranger_token}',
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_both_participants_receive_message_and_typing_indicator(self):
        alice_comm = WebsocketCommunicator(
            application, f'/ws/messaging/{self.conversation.id}/?token={self.alice_token}',
        )
        bob_comm = WebsocketCommunicator(
            application, f'/ws/messaging/{self.conversation.id}/?token={self.bob_token}',
        )

        self.assertTrue((await alice_comm.connect())[0])
        # Alice se connecte en premier : Bob la voit passer "online" à sa propre connexion.
        self.assertTrue((await bob_comm.connect())[0])
        alice_sees_bob_online = await alice_comm.receive_json_from()
        self.assertEqual(alice_sees_bob_online, {'type': 'presence', 'user_email': 'bob@example.com', 'status': 'online'})

        await alice_comm.send_to(text_data='{"type": "typing"}')
        bob_typing_event = await bob_comm.receive_json_from()
        self.assertEqual(bob_typing_event, {'type': 'typing', 'user_email': 'alice@example.com'})

        await alice_comm.send_to(text_data='{"content": "Coucou"}')
        alice_echo = await alice_comm.receive_json_from()
        bob_echo = await bob_comm.receive_json_from()
        self.assertEqual(alice_echo['content'], 'Coucou')
        self.assertEqual(bob_echo['content'], 'Coucou')

        await alice_comm.disconnect()
        await bob_comm.disconnect()

    async def test_message_is_persisted(self):
        communicator = WebsocketCommunicator(
            application, f'/ws/messaging/{self.conversation.id}/?token={self.alice_token}',
        )
        await communicator.connect()
        await communicator.send_to(text_data='{"content": "Persisted ?"}')
        await communicator.receive_json_from()
        await communicator.disconnect()

        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _count():
            return Message.objects.filter(conversation=self.conversation, content='Persisted ?').count()

        self.assertEqual(await _count(), 1)
