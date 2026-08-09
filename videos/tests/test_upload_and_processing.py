import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from videos.models import Video
from videos.services import TranscodingError

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='cstv_test_media_')


def _fake_video_file(name='clip.mp4'):
    return SimpleUploadedFile(name, b'fake-binary-video-content', content_type='video/mp4')


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoUploadPermissionTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email='creator@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.viewer = User.objects.create_user(email='viewer@example.com', password='S3curePass!23')

    @patch('videos.views.process_video.delay')
    def test_creator_can_upload_video_and_task_is_queued(self, mock_delay):
        self.client.force_authenticate(user=self.creator)
        response = self.client.post(reverse('videos:video-upload'), {
            'title': 'Mon film', 'visibility': 'public', 'source_file': _fake_video_file(),
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        video = Video.objects.get(id=response.data['id'])
        self.assertEqual(video.status, Video.Status.PENDING)
        self.assertEqual(video.owner, self.creator)
        mock_delay.assert_called_once_with(str(video.id))

    def test_plain_user_cannot_upload(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(reverse('videos:video-upload'), {
            'title': 'Mon film', 'source_file': _fake_video_file(),
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('videos.views.process_video.delay')
    def test_upload_rejects_unsupported_extension(self, mock_delay):
        self.client.force_authenticate(user=self.creator)
        bad_file = SimpleUploadedFile('doc.txt', b'not a video', content_type='text/plain')

        response = self.client.post(
            reverse('videos:video-upload'), {'title': 'x', 'source_file': bad_file}, format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_delay.assert_not_called()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoVisibilityTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')

        self.public_ready = Video.objects.create(
            owner=self.owner, title='Public Ready', status=Video.Status.READY,
            visibility=Video.Visibility.PUBLIC, source_file=_fake_video_file('a.mp4'),
        )
        self.private_ready = Video.objects.create(
            owner=self.owner, title='Private Ready', status=Video.Status.READY,
            visibility=Video.Visibility.PRIVATE, source_file=_fake_video_file('b.mp4'),
        )
        self.public_pending = Video.objects.create(
            owner=self.owner, title='Public Pending', status=Video.Status.PENDING,
            visibility=Video.Visibility.PUBLIC, source_file=_fake_video_file('c.mp4'),
        )

    def test_owner_sees_all_own_videos(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('videos:video-list'))
        self.assertEqual(response.data['count'], 3)

    def test_stranger_sees_only_public_ready_videos(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('videos:video-list'))
        titles = {v['title'] for v in response.data['results']}
        self.assertEqual(titles, {'Public Ready'})

    def test_stranger_cannot_retrieve_private_video(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('videos:video-detail', args=[self.private_ready.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_can_retrieve_public_ready_video(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('videos:video-detail', args=[self.public_ready.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stranger_cannot_delete_public_video(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.delete(reverse('videos:video-detail', args=[self.public_ready.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_own_video(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(reverse('videos:video-detail', args=[self.public_pending.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ProcessVideoTaskTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(owner=self.owner, title='Test', source_file=_fake_video_file())

    @patch('videos.tasks.services.build_master_playlist')
    @patch('videos.tasks.services.transcode_to_hls_rendition')
    @patch('videos.tasks.services.generate_thumbnail')
    @patch('videos.tasks.services.probe_video_height', return_value=1080)
    @patch('videos.tasks.services.probe_duration_seconds', return_value=120)
    def test_process_video_marks_ready_with_full_rendition_ladder(
        self, mock_duration, mock_height, mock_thumbnail, mock_transcode, mock_master,
    ):
        from videos.tasks import process_video
        process_video(str(self.video.id))

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.READY)
        self.assertEqual(self.video.duration_seconds, 120)
        self.assertEqual(set(self.video.renditions), {'1080p', '720p', '480p', '360p'})
        self.assertTrue(self.video.hls_master_playlist.endswith('master.m3u8'))
        self.assertEqual(mock_transcode.call_count, 4)

    @patch('videos.tasks.services.build_master_playlist')
    @patch('videos.tasks.services.transcode_to_hls_rendition')
    @patch('videos.tasks.services.generate_thumbnail')
    @patch('videos.tasks.services.probe_video_height', return_value=480)
    @patch('videos.tasks.services.probe_duration_seconds', return_value=60)
    def test_process_video_skips_renditions_above_source_resolution(
        self, mock_duration, mock_height, mock_thumbnail, mock_transcode, mock_master,
    ):
        from videos.tasks import process_video
        process_video(str(self.video.id))

        self.video.refresh_from_db()
        self.assertEqual(set(self.video.renditions), {'480p', '360p'})
        self.assertEqual(mock_transcode.call_count, 2)

    @patch('videos.tasks.services.probe_duration_seconds', side_effect=TranscodingError('ffprobe manquant'))
    def test_process_video_marks_failed_on_transcoding_error(self, mock_duration):
        from videos.tasks import process_video
        process_video(str(self.video.id))

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.FAILED)
        self.assertIn('ffprobe manquant', self.video.error_message)

    def test_process_video_ignores_unknown_id_silently(self):
        from videos.tasks import process_video
        process_video('00000000-0000-0000-0000-000000000000')
