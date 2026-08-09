import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.models import User
from live.models import LiveStream
from live.tasks import create_replay_from_stream
from videos.models import Video


class ReplayFromRecordingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='creator@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stream = LiveStream.objects.create(
            owner=self.owner, title='Émission du soir', visibility=LiveStream.Visibility.PUBLIC,
        )

    @patch('live.tasks.process_video.delay')
    def test_creates_and_links_replay_when_recording_exists(self, mock_process_video):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recording_dir = Path(tmp_dir) / self.stream.stream_key
            recording_dir.mkdir()
            recording_path = recording_dir / '2026-08-08_20-00-00.mp4'
            recording_path.write_bytes(b'fake-recording-bytes')

            with override_settings(LIVE_RECORDINGS_ROOT=tmp_dir):
                create_replay_from_stream(str(self.stream.id))

            self.stream.refresh_from_db()
            self.assertIsNotNone(self.stream.replay_video)
            self.assertEqual(self.stream.replay_video.owner, self.owner)
            self.assertEqual(self.stream.replay_video.visibility, Video.Visibility.PUBLIC)
            self.assertIn('Émission du soir', self.stream.replay_video.title)
            mock_process_video.assert_called_once_with(str(self.stream.replay_video.id))
            self.assertFalse(recording_path.exists(), 'le fichier source doit être nettoyé après copie')

    @patch('live.tasks.process_video.delay')
    def test_does_nothing_when_no_recording_found(self, mock_process_video):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with override_settings(LIVE_RECORDINGS_ROOT=tmp_dir):
                create_replay_from_stream(str(self.stream.id))

            self.stream.refresh_from_db()
            self.assertIsNone(self.stream.replay_video)
            mock_process_video.assert_not_called()

    @patch('live.tasks.process_video.delay')
    def test_does_not_duplicate_replay_if_already_linked(self, mock_process_video):
        existing_video = Video.objects.create(owner=self.owner, title='Déjà lié')
        self.stream.replay_video = existing_video
        self.stream.save(update_fields=['replay_video'])

        with tempfile.TemporaryDirectory() as tmp_dir:
            recording_dir = Path(tmp_dir) / self.stream.stream_key
            recording_dir.mkdir()
            (recording_dir / 'rec.mp4').write_bytes(b'fake')

            with override_settings(LIVE_RECORDINGS_ROOT=tmp_dir):
                create_replay_from_stream(str(self.stream.id))

        self.stream.refresh_from_db()
        self.assertEqual(self.stream.replay_video_id, existing_video.id)
        mock_process_video.assert_not_called()
