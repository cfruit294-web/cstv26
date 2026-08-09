from datetime import timedelta

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from config.asgi import application
from videos.models import Video
from watchparty.models import WatchParty, WatchPartyMembership


def _access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class WatchPartyConsumerTests(TransactionTestCase):
    def setUp(self):
        self.host = User.objects.create_user(email='host@example.com', password='S3curePass!23')
        self.member = User.objects.create_user(email='member@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.video = Video.objects.create(
            owner=self.host, title='Film test', visibility=Video.Visibility.PUBLIC, status=Video.Status.READY,
        )
        self.party = WatchParty.objects.create(
            host=self.host, video=self.video, scheduled_at=timezone.now() + timedelta(hours=1),
        )
        WatchPartyMembership.objects.create(
            party=self.party, user=self.member, status=WatchPartyMembership.Status.ACCEPTED,
        )
        # Générés en contexte synchrone : l'ORM refuse les écritures depuis un test async.
        self.host_token = _access_token_for(self.host)
        self.member_token = _access_token_for(self.member)
        self.stranger_token = _access_token_for(self.stranger)

    async def test_stranger_is_rejected(self):
        communicator = WebsocketCommunicator(
            application, f'/ws/watchparty/{self.party.id}/?token={self.stranger_token}',
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_accepted_member_can_connect_and_receives_sync_on_join(self):
        communicator = WebsocketCommunicator(
            application, f'/ws/watchparty/{self.party.id}/?token={self.member_token}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        sync = await communicator.receive_json_from()
        self.assertEqual(sync['type'], 'sync')
        self.assertEqual(sync['is_playing'], False)
        await communicator.disconnect()

    async def test_chat_message_is_broadcast_to_all_members(self):
        host_comm = WebsocketCommunicator(application, f'/ws/watchparty/{self.party.id}/?token={self.host_token}')
        member_comm = WebsocketCommunicator(application, f'/ws/watchparty/{self.party.id}/?token={self.member_token}')

        self.assertTrue((await host_comm.connect())[0])
        self.assertTrue((await member_comm.connect())[0])
        await host_comm.receive_json_from()  # sync
        await host_comm.receive_json_from()  # presence: member joining, broadcast to the rest of the group
        await member_comm.receive_json_from()  # sync (own join doesn't self-notify)

        await host_comm.send_to(text_data='{"type": "chat", "content": "Salut !"}')

        host_echo = await host_comm.receive_json_from()
        member_echo = await member_comm.receive_json_from()
        self.assertEqual(host_echo['type'], 'chat')
        self.assertEqual(host_echo['content'], 'Salut !')
        self.assertEqual(member_echo['content'], 'Salut !')

        await host_comm.disconnect()
        await member_comm.disconnect()

    async def test_member_cannot_control_playback(self):
        member_comm = WebsocketCommunicator(application, f'/ws/watchparty/{self.party.id}/?token={self.member_token}')
        self.assertTrue((await member_comm.connect())[0])
        await member_comm.receive_json_from()  # sync

        await member_comm.send_to(text_data='{"type": "playback", "action": "play", "position": 10}')
        self.assertTrue(await member_comm.receive_nothing(timeout=0.5), 'un simple membre ne doit pas pouvoir contrôler la lecture')

        await member_comm.disconnect()

    async def test_host_playback_control_is_broadcast_and_persisted(self):
        host_comm = WebsocketCommunicator(application, f'/ws/watchparty/{self.party.id}/?token={self.host_token}')
        member_comm = WebsocketCommunicator(application, f'/ws/watchparty/{self.party.id}/?token={self.member_token}')

        self.assertTrue((await host_comm.connect())[0])
        self.assertTrue((await member_comm.connect())[0])
        await host_comm.receive_json_from()  # sync
        await host_comm.receive_json_from()  # presence: member joining
        await member_comm.receive_json_from()  # sync

        await host_comm.send_to(text_data='{"type": "playback", "action": "play", "position": 42.5}')

        host_event = await host_comm.receive_json_from()
        member_event = await member_comm.receive_json_from()
        self.assertEqual(host_event['type'], 'playback')
        self.assertEqual(host_event['action'], 'play')
        self.assertEqual(host_event['position'], 42.5)
        self.assertTrue(host_event['is_playing'])
        self.assertEqual(member_event['position'], 42.5)

        await host_comm.disconnect()
        await member_comm.disconnect()

        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _refresh():
            self.party.refresh_from_db()

        await _refresh()
        self.assertTrue(self.party.is_playing)
        self.assertEqual(self.party.playback_position_seconds, 42.5)
