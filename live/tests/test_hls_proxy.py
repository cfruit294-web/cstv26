from unittest.mock import Mock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from live.models import LiveStream
from live.tokens import generate_live_hls_token


def _mock_upstream(content=b'#EXTM3U\n', content_type='application/vnd.apple.mpegurl', status_code=200):
    resp = Mock()
    resp.status_code = status_code
    resp.headers = {'Content-Type': content_type}
    resp.iter_content = Mock(return_value=iter([content]))
    return resp


class HlsPlaybackUrlSerializationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stream = LiveStream.objects.create(owner=self.owner, title='Show', visibility=LiveStream.Visibility.PUBLIC)

    def test_public_hls_playback_url_never_contains_stream_key(self):
        response = self.client.get(reverse('live:stream-detail', args=[self.stream.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.stream.stream_key, response.data['hls_playback_url'])
        self.assertIn(f'/api/v1/live/streams/{self.stream.id}/hls/', response.data['hls_playback_url'])

    def test_private_hls_playback_url_includes_a_signed_token(self):
        self.stream.visibility = LiveStream.Visibility.PRIVATE
        self.stream.save(update_fields=['visibility'])
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse('live:stream-detail', args=[self.stream.id]))
        self.assertIn('token=', response.data['hls_playback_url'])
        self.assertNotIn(self.stream.stream_key, response.data['hls_playback_url'])


class LiveHlsProxyViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.public_stream = LiveStream.objects.create(
            owner=self.owner, title='Public', visibility=LiveStream.Visibility.PUBLIC,
        )
        self.private_stream = LiveStream.objects.create(
            owner=self.owner, title='Private', visibility=LiveStream.Visibility.PRIVATE,
        )

    def _url(self, stream, relpath='index.m3u8'):
        return reverse('live:stream-hls', args=[stream.id, relpath])

    @patch('live.views.requests.get')
    def test_anonymous_can_stream_public_live(self, mock_get):
        mock_get.return_value = _mock_upstream()
        response = self.client.get(self._url(self.public_stream))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        upstream_url = mock_get.call_args[0][0]
        self.assertIn(self.public_stream.stream_key, upstream_url)
        self.assertEqual(b''.join(response.streaming_content), b'#EXTM3U\n')

    @patch('live.views.requests.get')
    def test_canceled_public_stream_is_not_playable(self, mock_get):
        self.public_stream.status = LiveStream.Status.CANCELED
        self.public_stream.save(update_fields=['status'])
        response = self.client.get(self._url(self.public_stream))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_get.assert_not_called()

    @patch('live.views.requests.get')
    def test_private_stream_without_token_or_ownership_is_rejected(self, mock_get):
        response = self.client.get(self._url(self.private_stream))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_get.assert_not_called()

    @patch('live.views.requests.get')
    def test_private_stream_stranger_with_someone_elses_token_is_rejected(self, mock_get):
        other_stream = LiveStream.objects.create(
            owner=self.owner, title='Other private', visibility=LiveStream.Visibility.PRIVATE,
        )
        token = generate_live_hls_token(other_stream.id)
        response = self.client.get(f'{self._url(self.private_stream)}?token={token}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_get.assert_not_called()

    @patch('live.views.requests.get')
    def test_private_stream_with_valid_token_is_playable(self, mock_get):
        mock_get.return_value = _mock_upstream()
        token = generate_live_hls_token(self.private_stream.id)
        response = self.client.get(f'{self._url(self.private_stream)}?token={token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('live.views.requests.get')
    def test_owner_can_stream_own_private_live_without_token(self, mock_get):
        mock_get.return_value = _mock_upstream()
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self._url(self.private_stream))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('live.views.requests.get')
    def test_stranger_authenticated_but_not_owner_needs_token(self, mock_get):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(self._url(self.private_stream))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_get.assert_not_called()

    @patch('live.views.requests.get')
    def test_upstream_failure_returns_404(self, mock_get):
        mock_get.return_value = _mock_upstream(status_code=502)
        response = self.client.get(self._url(self.public_stream))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_stream_returns_404(self):
        response = self.client.get(
            reverse('live:stream-hls', args=['00000000-0000-0000-0000-000000000000', 'index.m3u8']),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
