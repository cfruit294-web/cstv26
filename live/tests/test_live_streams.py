from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from live.models import LiveChatMessage, LiveStream


class LiveStreamCreationTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email='creator@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.viewer = User.objects.create_user(email='viewer@example.com', password='S3curePass!23')

    def test_creator_can_schedule_live_stream(self):
        self.client.force_authenticate(user=self.creator)
        response = self.client.post(reverse('live:stream-create'), {
            'title': 'Concert live', 'visibility': 'public',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        stream = LiveStream.objects.get(title='Concert live')
        self.assertEqual(stream.owner, self.creator)
        self.assertEqual(stream.status, LiveStream.Status.SCHEDULED)
        self.assertTrue(stream.stream_key)

    def test_plain_user_cannot_schedule_live_stream(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(reverse('live:stream-create'), {'title': 'x'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stream_key_is_unique_per_stream(self):
        self.client.force_authenticate(user=self.creator)
        r1 = self.client.post(reverse('live:stream-create'), {'title': 'A'})
        r2 = self.client.post(reverse('live:stream-create'), {'title': 'B'})
        s1 = LiveStream.objects.get(id=r1.data['id'])
        s2 = LiveStream.objects.get(id=r2.data['id'])
        self.assertNotEqual(s1.stream_key, s2.stream_key)


class LiveStreamAccessTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.public_stream = LiveStream.objects.create(owner=self.owner, title='Public', visibility=LiveStream.Visibility.PUBLIC)
        self.private_stream = LiveStream.objects.create(owner=self.owner, title='Private', visibility=LiveStream.Visibility.PRIVATE)

    def test_owner_sees_stream_key_in_detail(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('live:stream-detail', args=[self.public_stream.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('stream_key', response.data)
        self.assertIn('rtmp_ingest_url', response.data)

    def test_stranger_does_not_see_stream_key(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('live:stream-detail', args=[self.public_stream.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('stream_key', response.data)
        self.assertNotIn('rtmp_ingest_url', response.data)

    def test_stranger_cannot_access_private_stream(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('live:stream-detail', args=[self.private_stream.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_excludes_private_streams_for_strangers(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('live:stream-list'))
        titles = {s['title'] for s in response.data['results']}
        self.assertEqual(titles, {'Public'})

    def test_anonymous_visitor_can_list_public_streams(self):
        response = self.client.get(reverse('live:stream-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {s['title'] for s in response.data['results']}
        self.assertEqual(titles, {'Public'})

    def test_anonymous_visitor_can_view_public_stream_detail(self):
        response = self.client.get(reverse('live:stream-detail', args=[self.public_stream.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('stream_key', response.data)

    def test_anonymous_visitor_cannot_view_private_stream(self):
        response = self.client.get(reverse('live:stream-detail', args=[self.private_stream.id]))
        # 401 (pas 403) : aucun jeton n'a été présenté, distinct du cas "authentifié mais non autorisé".
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LiveStreamLifecycleTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.stream = LiveStream.objects.create(owner=self.owner, title='Show')

    def test_owner_can_start_and_end_stream(self):
        self.client.force_authenticate(user=self.owner)

        start_response = self.client.post(reverse('live:stream-start', args=[self.stream.id]))
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        self.assertEqual(start_response.data['status'], 'live')

        end_response = self.client.post(reverse('live:stream-end', args=[self.stream.id]))
        self.assertEqual(end_response.data['status'], 'ended')

    def test_stranger_cannot_start_someone_elses_stream(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(reverse('live:stream-start', args=[self.stream.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RtmpWebhookTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stream = LiveStream.objects.create(owner=self.owner, title='Show')

    def test_publish_event_marks_stream_live(self):
        response = self.client.post(reverse('live:rtmp-webhook'), {
            'secret': settings.RTMP_WEBHOOK_SECRET, 'name': self.stream.stream_key, 'event': 'publish',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stream.refresh_from_db()
        self.assertEqual(self.stream.status, LiveStream.Status.LIVE)

    def test_publish_done_event_marks_stream_ended(self):
        self.client.post(reverse('live:rtmp-webhook'), {
            'secret': settings.RTMP_WEBHOOK_SECRET, 'name': self.stream.stream_key, 'event': 'publish',
        })
        response = self.client.post(reverse('live:rtmp-webhook'), {
            'secret': settings.RTMP_WEBHOOK_SECRET, 'name': self.stream.stream_key, 'event': 'publish_done',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stream.refresh_from_db()
        self.assertEqual(self.stream.status, LiveStream.Status.ENDED)

    def test_webhook_rejects_wrong_secret(self):
        response = self.client.post(reverse('live:rtmp-webhook'), {
            'secret': 'wrong', 'name': self.stream.stream_key, 'event': 'publish',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_webhook_unknown_stream_key_returns_404(self):
        response = self.client.post(reverse('live:rtmp-webhook'), {
            'secret': settings.RTMP_WEBHOOK_SECRET, 'name': 'unknown-key', 'event': 'publish',
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LiveChatHistoryTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.stream = LiveStream.objects.create(owner=self.owner, title='Show', visibility=LiveStream.Visibility.PUBLIC)
        LiveChatMessage.objects.create(stream=self.stream, user=self.owner, message='Bienvenue !')

    def test_anyone_can_read_public_stream_chat_history(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('live:stream-chat', args=[self.stream.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_chat_history_forbidden_for_private_stream_strangers(self):
        self.stream.visibility = LiveStream.Visibility.PRIVATE
        self.stream.save(update_fields=['visibility'])
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('live:stream-chat', args=[self.stream.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
