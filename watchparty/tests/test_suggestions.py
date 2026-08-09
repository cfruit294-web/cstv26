from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import Movie
from videos.models import Video
from watchparty.models import WatchParty, WatchPartyMembership


def _make_movie(imdb_id, title, genre, rating):
    return Movie.objects.create(imdb_id=imdb_id, title=title, genre=genre, imdb_rating=rating)


def _make_eligible_video(owner, movie, title):
    return Video.objects.create(
        owner=owner, movie=movie, title=title, visibility=Video.Visibility.PUBLIC, status=Video.Status.READY,
    )


class WatchPartySuggestionsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')

        self.action_movie = _make_movie('tt001', 'Grosse Explosion', 'Action, Thriller', '7.0')
        self.comedy_movie = _make_movie('tt002', 'Rire aux éclats', 'Comédie', '8.5')
        self.no_video_movie = _make_movie('tt003', 'Introuvable', 'Action', '9.9')

        _make_eligible_video(self.other, self.action_movie, 'Grosse Explosion - vidéo')
        _make_eligible_video(self.other, self.comedy_movie, 'Rire aux éclats - vidéo')
        # no_video_movie n'a volontairement aucune vidéo : ne doit jamais être suggéré.

    def test_requires_authentication(self):
        response = self.client.get(reverse('watchparty:party-suggestions'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_history_returns_top_rated_eligible_movies(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('watchparty:party-suggestions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [movie['title'] for movie in response.data]
        self.assertIn('Rire aux éclats', titles)
        self.assertIn('Grosse Explosion', titles)
        self.assertNotIn('Introuvable', titles, 'un film sans vidéo éligible ne doit jamais être suggéré')
        # Sans historique : triés par note, la comédie (8.5) doit passer avant l'action (7.0).
        self.assertLess(titles.index('Rire aux éclats'), titles.index('Grosse Explosion'))

    def test_with_hosting_history_prioritizes_matching_genre(self):
        past_party = WatchParty.objects.create(
            host=self.user, video=self.action_movie.videos.first(), scheduled_at=timezone.now() - timedelta(days=1),
            status=WatchParty.Status.ENDED,
        )
        self.assertEqual(past_party.video.movie, self.action_movie)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('watchparty:party-suggestions'))
        titles = [movie['title'] for movie in response.data]
        # Ayant déjà organisé une séance "Action", ce genre doit passer devant la comédie mieux notée.
        self.assertEqual(titles[0], 'Grosse Explosion')

    def test_attended_party_also_counts_as_taste_signal(self):
        party = WatchParty.objects.create(
            host=self.other, video=self.action_movie.videos.first(), scheduled_at=timezone.now() - timedelta(days=1),
        )
        WatchPartyMembership.objects.create(
            party=party, user=self.user, status=WatchPartyMembership.Status.ACCEPTED,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('watchparty:party-suggestions'))
        titles = [movie['title'] for movie in response.data]
        self.assertEqual(titles[0], 'Grosse Explosion')
