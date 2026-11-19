"""Pipeline vidéo avec un stockage distant (S3 & co).

InMemoryStorage joue le rôle du bucket : comme S3Storage, il n'a pas de chemin disque
(`path()` lève NotImplementedError), ce qui force exactement les mêmes chemins de code que S3 :
téléchargement de la source, envoi du HLS, redirection vers une URL signée.
"""
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage, default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from core.storage import delete_prefix, is_local_storage, upload_directory
from videos.models import Video
from videos.tokens import generate_hls_token

REMOTE_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
SOURCE_BYTES = b'fake-binary-video-content'


def _fake_transcode(source_path, output_dir, *args, **kwargs):
    # Vérifie que ffmpeg reçoit bien une copie locale fidèle de la source stockée à distance.
    assert Path(source_path).read_bytes() == SOURCE_BYTES
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'segment_000.ts').write_bytes(b'ts-data')
    (output_dir / 'playlist.m3u8').write_text('#EXTM3U\nsegment_000.ts\n')


def _fake_thumbnail(source_path, output_path, *args, **kwargs):
    output_path.write_bytes(b'jpeg-data')


@override_settings(STORAGES=REMOTE_STORAGES)
class RemoteStorageProcessingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(
            owner=self.owner, title='Remote',
            source_file=SimpleUploadedFile('clip.mp4', SOURCE_BYTES, content_type='video/mp4'),
        )

    def test_storage_is_detected_as_remote(self):
        self.assertFalse(is_local_storage())

    @patch('videos.tasks.services.transcode_to_hls_rendition', side_effect=_fake_transcode)
    @patch('videos.tasks.services.generate_thumbnail', side_effect=_fake_thumbnail)
    @patch('videos.tasks.services.probe_video_height', return_value=480)
    @patch('videos.tasks.services.probe_duration_seconds', return_value=60)
    def test_process_video_uploads_hls_and_thumbnail_to_storage(self, *mocks):
        from videos.tasks import process_video
        process_video(str(self.video.id))

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.READY, self.video.error_message)
        prefix = f'hls/{self.video.id}'
        for name in ('master.m3u8', '480p/playlist.m3u8', '480p/segment_000.ts', '360p/segment_000.ts'):
            self.assertTrue(default_storage.exists(f'{prefix}/{name}'), name)
        self.assertEqual(self.video.thumbnail.name, f'videos/thumbnails/{self.video.id}.jpg')
        self.assertTrue(default_storage.exists(self.video.thumbnail.name))

    @patch('videos.tasks.services.transcode_to_hls_rendition', side_effect=_fake_transcode)
    @patch('videos.tasks.services.generate_thumbnail', side_effect=_fake_thumbnail)
    @patch('videos.tasks.services.probe_video_height', return_value=360)
    @patch('videos.tasks.services.probe_duration_seconds', return_value=60)
    def test_reprocessing_replaces_previous_output_without_renaming(self, *mocks):
        stale = f'hls/{self.video.id}/1080p/segment_999.ts'
        default_storage.save(stale, ContentFile(b'old'))

        from videos.tasks import process_video
        process_video(str(self.video.id))
        process_video(str(self.video.id))  # un "Relancer" ne doit pas créer de doublons renommés

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.READY, self.video.error_message)
        self.assertFalse(default_storage.exists(stale))
        self.assertEqual(self.video.thumbnail.name, f'videos/thumbnails/{self.video.id}.jpg')

    @patch('videos.tasks.upload_directory', side_effect=OSError('bucket injoignable'))
    @patch('videos.tasks.services.transcode_to_hls_rendition', side_effect=_fake_transcode)
    @patch('videos.tasks.services.generate_thumbnail', side_effect=_fake_thumbnail)
    @patch('videos.tasks.services.probe_video_height', return_value=360)
    @patch('videos.tasks.services.probe_duration_seconds', return_value=60)
    def test_storage_failure_marks_video_failed_instead_of_stuck_processing(self, *mocks):
        from videos.tasks import process_video
        process_video(str(self.video.id))

        self.video.refresh_from_db()
        self.assertEqual(self.video.status, Video.Status.FAILED)
        self.assertIn('bucket injoignable', self.video.error_message)


@override_settings(STORAGES=REMOTE_STORAGES)
class RemoteStorageHlsServingTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(
            owner=owner, title='Ready', status=Video.Status.READY, visibility=Video.Visibility.PUBLIC,
            source_file=SimpleUploadedFile('clip.mp4', SOURCE_BYTES, content_type='video/mp4'),
        )
        prefix = f'hls/{self.video.id}'
        default_storage.save(f'{prefix}/master.m3u8', ContentFile(b'#EXTM3U\n360p/playlist.m3u8\n'))
        default_storage.save(f'{prefix}/360p/segment_000.ts', ContentFile(b'ts-data'))
        self.token = generate_hls_token(self.video.id)

    def _url(self, relpath, token=None):
        url = reverse('protected-hls', args=[self.video.id, relpath])
        return f'{url}?token={token or self.token}'

    def test_manifest_is_read_from_storage_and_token_propagated(self):
        response = self.client.get(self._url('master.m3u8'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'360p/playlist.m3u8?token={self.token}', response.content.decode())

    def test_segment_redirects_to_short_lived_signed_url(self):
        with patch.object(InMemoryStorage, 'url', create=True, return_value='https://bucket.example/sig') as mock_url:
            response = self.client.get(self._url('360p/segment_000.ts'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://bucket.example/sig')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        name = mock_url.call_args.args[0]
        self.assertEqual(name, f'hls/{self.video.id}/360p/segment_000.ts')
        self.assertEqual(mock_url.call_args.kwargs['parameters'], {'ResponseContentType': 'video/mp2t'})

    def test_invalid_token_never_gets_a_signed_url(self):
        with patch.object(InMemoryStorage, 'url', create=True) as mock_url:
            response = self.client.get(self._url('360p/segment_000.ts', token='bad'))
        self.assertEqual(response.status_code, 404)
        mock_url.assert_not_called()

    def test_traversal_outside_video_prefix_is_rejected(self):
        with patch.object(InMemoryStorage, 'url', create=True) as mock_url:
            response = self.client.get(self._url('../other-video/master.m3u8'))
        self.assertEqual(response.status_code, 404)
        mock_url.assert_not_called()

    def test_missing_manifest_returns_404(self):
        response = self.client.get(self._url('720p/playlist.m3u8'))
        self.assertEqual(response.status_code, 404)


@override_settings(STORAGES=REMOTE_STORAGES)
class StorageHelpersTests(TestCase):
    def test_upload_directory_replaces_prefix_contents(self, ):
        import tempfile
        default_storage.save('hls/x/old.ts', ContentFile(b'old'))
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'a').mkdir()
            (Path(tmp) / 'a' / 'new.ts').write_bytes(b'new')
            upload_directory(tmp, 'hls/x')

        self.assertFalse(default_storage.exists('hls/x/old.ts'))
        with default_storage.open('hls/x/a/new.ts') as fh:
            self.assertEqual(fh.read(), b'new')

    def test_delete_prefix_on_missing_prefix_is_noop(self):
        delete_prefix('hls/does-not-exist')
