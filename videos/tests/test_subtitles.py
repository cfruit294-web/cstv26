import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from videos.models import Subtitle, Video
from videos.tokens import generate_hls_token

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='cstv_test_subtitles_')


def _vtt_file(name='fr.vtt'):
    return SimpleUploadedFile(name, b'WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nSalut', content_type='text/vtt')


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class SubtitleUploadTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stranger = User.objects.create_user(
            email='stranger@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(
            owner=self.owner, title='Mon film', status=Video.Status.READY,
            source_file=SimpleUploadedFile('src.mp4', b'fake', content_type='video/mp4'),
        )

    def test_owner_can_upload_subtitle(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse('videos:video-subtitle-upload', args=[self.video.id]),
            {'language': 'fr', 'file': _vtt_file()},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Subtitle.objects.filter(video=self.video, language='fr').count(), 1)

    def test_cannot_upload_two_subtitles_same_language(self):
        Subtitle.objects.create(video=self.video, language='fr', file=_vtt_file())
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse('videos:video-subtitle-upload', args=[self.video.id]),
            {'language': 'fr', 'file': _vtt_file('fr2.vtt')},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_non_vtt_file(self):
        self.client.force_authenticate(user=self.owner)
        bad_file = SimpleUploadedFile('fr.srt', b'not vtt', content_type='text/plain')
        response = self.client.post(
            reverse('videos:video-subtitle-upload', args=[self.video.id]),
            {'language': 'fr', 'file': bad_file},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stranger_cannot_upload_subtitle_for_others_video(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(
            reverse('videos:video-subtitle-upload', args=[self.video.id]),
            {'language': 'en', 'file': _vtt_file('en.vtt')},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_subtitle(self):
        subtitle = Subtitle.objects.create(video=self.video, language='en', file=_vtt_file('en.vtt'))
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(reverse('videos:subtitle-delete', args=[subtitle.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Subtitle.objects.filter(id=subtitle.id).exists())

    def test_stranger_cannot_delete_subtitle(self):
        subtitle = Subtitle.objects.create(video=self.video, language='en', file=_vtt_file('en.vtt'))
        self.client.force_authenticate(user=self.stranger)
        response = self.client.delete(reverse('videos:subtitle-delete', args=[subtitle.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Subtitle.objects.filter(id=subtitle.id).exists())


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoSerializerSubtitlesTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner2@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(
            owner=self.owner, title='Sous-titré', status=Video.Status.READY,
            visibility=Video.Visibility.PUBLIC,
            source_file=SimpleUploadedFile('src.mp4', b'fake', content_type='video/mp4'),
        )
        Subtitle.objects.create(video=self.video, language='fr', file=_vtt_file('fr.vtt'))
        Subtitle.objects.create(video=self.video, language='en', file=_vtt_file('en.vtt'))

    def test_video_detail_exposes_both_subtitle_languages(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('videos:video-detail', args=[self.video.id]))
        languages = {s['language'] for s in response.data['subtitles']}
        self.assertEqual(languages, {'fr', 'en'})
        for subtitle in response.data['subtitles']:
            self.assertIn('token=', subtitle['url'])


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ProtectedSubtitleFileViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner3@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(
            owner=self.owner, title='Test', status=Video.Status.READY,
            source_file=SimpleUploadedFile('src.mp4', b'fake', content_type='video/mp4'),
        )
        self.subtitle = Subtitle.objects.create(video=self.video, language='fr', file=_vtt_file())

    def test_valid_token_serves_vtt_file(self):
        token = generate_hls_token(self.video.id)
        url = reverse('protected-subtitle', args=[self.video.id, 'fr'])
        response = self.client.get(f'{url}?token={token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_token_returns_404(self):
        url = reverse('protected-subtitle', args=[self.video.id, 'fr'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_video_token_returns_404(self):
        other_video = Video.objects.create(
            owner=self.owner, title='Autre', status=Video.Status.READY,
            source_file=SimpleUploadedFile('other.mp4', b'fake', content_type='video/mp4'),
        )
        token = generate_hls_token(other_video.id)
        url = reverse('protected-subtitle', args=[self.video.id, 'fr'])
        response = self.client.get(f'{url}?token={token}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
