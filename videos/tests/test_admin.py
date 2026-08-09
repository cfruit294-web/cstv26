import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from videos.models import Video

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='cstv_test_admin_media_')


def _fake_video_file(name='clip.mp4'):
    return SimpleUploadedFile(name, b'fake-binary-video-content', content_type='video/mp4')


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoAdminTranscodingTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(email='root@example.com', password='S3curePass!23')
        self.client.force_login(self.admin_user)

    @patch('videos.admin.process_video.delay')
    def test_adding_video_from_admin_queues_transcoding(self, mock_delay):
        response = self.client.post(reverse('admin:videos_video_add'), {
            'owner': self.admin_user.id,
            'title': 'Film ajouté à la main',
            'description': '',
            'visibility': Video.Visibility.PUBLIC,
            'status': Video.Status.PENDING,
            'source_file': _fake_video_file(),
            'subtitles-TOTAL_FORMS': '0',
            'subtitles-INITIAL_FORMS': '0',
            'subtitles-MIN_NUM_FORMS': '0',
            'subtitles-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302, response.content)

        video = Video.objects.get(title='Film ajouté à la main')
        self.assertEqual(video.status, Video.Status.PENDING)
        mock_delay.assert_called_once_with(str(video.id))

    @patch('videos.admin.process_video.delay')
    def test_replacing_source_file_requeues_transcoding(self, mock_delay):
        video = Video.objects.create(
            owner=self.admin_user, title='Déjà là', status=Video.Status.READY,
            source_file=_fake_video_file('old.mp4'),
        )
        mock_delay.reset_mock()

        response = self.client.post(reverse('admin:videos_video_change', args=[video.id]), {
            'owner': self.admin_user.id,
            'title': video.title,
            'description': '',
            'visibility': Video.Visibility.PRIVATE,
            'status': video.status,
            'source_file': _fake_video_file('new.mp4'),
            'subtitles-TOTAL_FORMS': '0',
            'subtitles-INITIAL_FORMS': '0',
            'subtitles-MIN_NUM_FORMS': '0',
            'subtitles-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302, response.content)

        video.refresh_from_db()
        self.assertEqual(video.status, Video.Status.PENDING)
        mock_delay.assert_called_once_with(str(video.id))

    @patch('videos.admin.process_video.delay')
    def test_editing_without_changing_file_does_not_requeue(self, mock_delay):
        video = Video.objects.create(
            owner=self.admin_user, title='Stable', status=Video.Status.READY,
            source_file=_fake_video_file('stable.mp4'),
        )

        response = self.client.post(reverse('admin:videos_video_change', args=[video.id]), {
            'owner': self.admin_user.id,
            'title': 'Stable (renommé)',
            'description': '',
            'visibility': Video.Visibility.PRIVATE,
            'status': video.status,
            'subtitles-TOTAL_FORMS': '0',
            'subtitles-INITIAL_FORMS': '0',
            'subtitles-MIN_NUM_FORMS': '0',
            'subtitles-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302, response.content)

        video.refresh_from_db()
        self.assertEqual(video.status, Video.Status.READY)
        mock_delay.assert_not_called()
