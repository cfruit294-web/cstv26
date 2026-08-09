from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import Movie
from library.models import WatchHistory, WatchlistItem
from videos.models import Video


def _movie(**kwargs):
    defaults = {'imdb_id': f'tt{Movie.objects.count() + 1:07d}', 'title': 'Film', 'type': Movie.Type.MOVIE}
    defaults.update(kwargs)
    return Movie.objects.create(**defaults)


class WatchlistTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.movie = _movie(title='Dune')

    def test_requires_authentication(self):
        response = self.client.post(reverse('library:watchlist-toggle'), {'movie_id': self.movie.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_toggle_adds_then_removes(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('library:watchlist-toggle')

        response = self.client.post(url, {'movie_id': self.movie.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['in_watchlist'])
        self.assertEqual(WatchlistItem.objects.filter(user=self.user, movie=self.movie).count(), 1)

        response = self.client.post(url, {'movie_id': self.movie.id})
        self.assertFalse(response.data['in_watchlist'])
        self.assertEqual(WatchlistItem.objects.filter(user=self.user, movie=self.movie).count(), 0)

    def test_status_reflects_watchlist(self):
        self.client.force_authenticate(user=self.user)
        status_url = reverse('library:watchlist-status', args=[self.movie.id])

        self.assertFalse(self.client.get(status_url).data['in_watchlist'])
        WatchlistItem.objects.create(user=self.user, movie=self.movie)
        self.assertTrue(self.client.get(status_url).data['in_watchlist'])

    def test_list_only_returns_own_items(self):
        stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        WatchlistItem.objects.create(user=self.user, movie=self.movie)
        WatchlistItem.objects.create(user=stranger, movie=_movie(title='Autre film'))

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('library:watchlist-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['movie']['title'], 'Dune')


class WatchHistoryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.video = Video.objects.create(
            owner=self.user, title='Episode', status=Video.Status.READY,
            source_file=SimpleUploadedFile('src.mp4', b'fake', content_type='video/mp4'),
        )

    def test_no_history_returns_zero(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('library:history-detail', args=[self.video.id]))
        self.assertEqual(response.data['position_seconds'], 0)

    def test_update_then_retrieve_position(self):
        self.client.force_authenticate(user=self.user)
        update_url = reverse('library:history-update')

        response = self.client.post(update_url, {'video': self.video.id, 'position_seconds': 128})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WatchHistory.objects.get(user=self.user, video=self.video).position_seconds, 128)

        response = self.client.get(reverse('library:history-detail', args=[self.video.id]))
        self.assertEqual(response.data['position_seconds'], 128)

    def test_second_update_overwrites_position(self):
        self.client.force_authenticate(user=self.user)
        update_url = reverse('library:history-update')

        self.client.post(update_url, {'video': self.video.id, 'position_seconds': 50})
        self.client.post(update_url, {'video': self.video.id, 'position_seconds': 90})

        self.assertEqual(WatchHistory.objects.filter(user=self.user, video=self.video).count(), 1)
        self.assertEqual(WatchHistory.objects.get(user=self.user, video=self.video).position_seconds, 90)

    def test_history_is_scoped_per_user(self):
        other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        WatchHistory.objects.create(user=other, video=self.video, position_seconds=999)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('library:history-detail', args=[self.video.id]))
        self.assertEqual(response.data['position_seconds'], 0)
