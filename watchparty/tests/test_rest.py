from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from videos.models import Video
from watchparty.models import WatchParty, WatchPartyMembership


def _make_video(owner, visibility=Video.Visibility.PUBLIC, video_status=Video.Status.READY, title='Film test'):
    return Video.objects.create(owner=owner, title=title, visibility=visibility, status=video_status)


class WatchPartyCreationTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(email='host@example.com', password='S3curePass!23')
        self.video = _make_video(self.host)

    def test_any_authenticated_user_can_create_party_with_public_ready_video(self):
        self.client.force_authenticate(user=self.host)
        response = self.client.post(reverse('watchparty:party-list'), {
            'video': str(self.video.id),
            'title': 'Soirée ciné',
            'scheduled_at': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['my_status'], 'host')
        self.assertIsNotNone(response.data['video'])
        party = WatchParty.objects.get(id=response.data['id'])
        self.assertEqual(party.host, self.host)

    def test_cannot_create_party_with_private_video(self):
        private_video = _make_video(self.host, visibility=Video.Visibility.PRIVATE)
        self.client.force_authenticate(user=self.host)
        response = self.client.post(reverse('watchparty:party-list'), {
            'video': str(private_video.id),
            'scheduled_at': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_party_with_video_not_ready(self):
        processing_video = _make_video(self.host, video_status=Video.Status.PROCESSING)
        self.client.force_authenticate(user=self.host)
        response = self.client.post(reverse('watchparty:party-list'), {
            'video': str(processing_video.id),
            'scheduled_at': (timezone.now() + timedelta(hours=2)).isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WatchPartyVisibilityTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(email='host@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.video = _make_video(self.host)
        self.party = WatchParty.objects.create(
            host=self.host, video=self.video, title='Soirée', scheduled_at=timezone.now() + timedelta(hours=1),
        )

    def test_stranger_sees_party_but_not_video(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('watchparty:party-detail', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['my_status'])
        self.assertIsNone(response.data['video'])
        self.assertIsNone(response.data['current_position_seconds'])
        # Les infos non sensibles (titre du film, vignette) restent visibles pour donner envie de rejoindre.
        self.assertEqual(response.data['video_title'], self.video.title)

    def test_host_sees_video(self):
        self.client.force_authenticate(user=self.host)
        response = self.client.get(reverse('watchparty:party-detail', args=[self.party.id]))
        self.assertEqual(response.data['my_status'], 'host')
        self.assertIsNotNone(response.data['video'])


class WatchPartyJoinAndModerationTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(email='host@example.com', password='S3curePass!23')
        self.alice = User.objects.create_user(email='alice@example.com', password='S3curePass!23')
        self.bob = User.objects.create_user(email='bob@example.com', password='S3curePass!23')
        self.video = _make_video(self.host)
        self.party = WatchParty.objects.create(
            host=self.host, video=self.video, scheduled_at=timezone.now() + timedelta(hours=1),
        )

    def test_join_creates_pending_membership(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')

        detail = self.client.get(reverse('watchparty:party-detail', args=[self.party.id]))
        self.assertEqual(detail.data['my_status'], 'pending')

    def test_cannot_join_twice_while_pending(self):
        self.client.force_authenticate(user=self.alice)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        second = self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_host_cannot_join_own_party(self):
        self.client.force_authenticate(user=self.host)
        response = self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stranger_cannot_list_membership_requests(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.get(reverse('watchparty:party-members', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_host_can_accept_join_request(self):
        self.client.force_authenticate(user=self.alice)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        membership = WatchPartyMembership.objects.get(party=self.party, user=self.alice)

        self.client.force_authenticate(user=self.host)
        response = self.client.post(
            reverse('watchparty:party-member-accept', args=[self.party.id, membership.id]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')

        self.client.force_authenticate(user=self.alice)
        detail = self.client.get(reverse('watchparty:party-detail', args=[self.party.id]))
        self.assertEqual(detail.data['my_status'], 'member')
        self.assertIsNotNone(detail.data['video'])

    def test_host_can_reject_join_request(self):
        self.client.force_authenticate(user=self.alice)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        membership = WatchPartyMembership.objects.get(party=self.party, user=self.alice)

        self.client.force_authenticate(user=self.host)
        response = self.client.post(
            reverse('watchparty:party-member-reject', args=[self.party.id, membership.id]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'rejected')

    def test_accepted_member_cannot_accept_others(self):
        self.client.force_authenticate(user=self.alice)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        alice_membership = WatchPartyMembership.objects.get(party=self.party, user=self.alice)
        self.client.force_authenticate(user=self.host)
        self.client.post(reverse('watchparty:party-member-accept', args=[self.party.id, alice_membership.id]))

        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        bob_membership = WatchPartyMembership.objects.get(party=self.party, user=self.bob)

        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            reverse('watchparty:party-member-accept', args=[self.party.id, bob_membership.id]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_host_can_promote_accepted_member_who_can_then_moderate(self):
        self.client.force_authenticate(user=self.alice)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        alice_membership = WatchPartyMembership.objects.get(party=self.party, user=self.alice)
        self.client.force_authenticate(user=self.host)
        self.client.post(reverse('watchparty:party-member-accept', args=[self.party.id, alice_membership.id]))

        promote_response = self.client.post(
            reverse('watchparty:party-member-promote', args=[self.party.id, alice_membership.id]),
        )
        self.assertEqual(promote_response.status_code, status.HTTP_200_OK)
        self.assertEqual(promote_response.data['role'], 'moderator')

        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        bob_membership = WatchPartyMembership.objects.get(party=self.party, user=self.bob)

        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            reverse('watchparty:party-member-accept', args=[self.party.id, bob_membership.id]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_host_can_promote(self):
        self.client.force_authenticate(user=self.alice)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        alice_membership = WatchPartyMembership.objects.get(party=self.party, user=self.alice)
        self.client.force_authenticate(user=self.host)
        self.client.post(reverse('watchparty:party-member-accept', args=[self.party.id, alice_membership.id]))

        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('watchparty:party-join', args=[self.party.id]))
        bob_membership = WatchPartyMembership.objects.get(party=self.party, user=self.bob)

        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            reverse('watchparty:party-member-promote', args=[self.party.id, bob_membership.id]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WatchPartyLifecycleTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(email='host@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.video = _make_video(self.host)
        self.party = WatchParty.objects.create(
            host=self.host, video=self.video, scheduled_at=timezone.now() + timedelta(hours=1),
        )

    def test_host_can_start_and_end(self):
        self.client.force_authenticate(user=self.host)
        start = self.client.post(reverse('watchparty:party-start', args=[self.party.id]))
        self.assertEqual(start.data['status'], 'live')
        end = self.client.post(reverse('watchparty:party-end', args=[self.party.id]))
        self.assertEqual(end.data['status'], 'ended')

    def test_stranger_cannot_start(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(reverse('watchparty:party-start', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_host_can_cancel_scheduled_party(self):
        self.client.force_authenticate(user=self.host)
        response = self.client.post(reverse('watchparty:party-cancel', args=[self.party.id]))
        self.assertEqual(response.data['status'], 'canceled')

    def test_cannot_cancel_live_party(self):
        self.client.force_authenticate(user=self.host)
        self.client.post(reverse('watchparty:party-start', args=[self.party.id]))
        response = self.client.post(reverse('watchparty:party-cancel', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WatchPartyChatHistoryTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(email='host@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.video = _make_video(self.host)
        self.party = WatchParty.objects.create(
            host=self.host, video=self.video, scheduled_at=timezone.now() + timedelta(hours=1),
        )

    def test_stranger_cannot_read_chat_history(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('watchparty:party-chat', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_host_can_read_chat_history(self):
        self.client.force_authenticate(user=self.host)
        response = self.client.get(reverse('watchparty:party-chat', args=[self.party.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
