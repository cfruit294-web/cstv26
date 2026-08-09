from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import Movie
from community.models import Post
from live.models import LiveStream
from videos.models import Video


class GlobalSearchTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='S3curePass!23')

        Movie.objects.create(imdb_id='tt0001', title='Star Wars Origins', year='2020')
        Post.objects.create(author=self.owner, content='J\'adore Star Wars')

        self.public_ready_video = Video.objects.create(
            owner=self.owner, title='Star Wars Trailer', status=Video.Status.READY,
            visibility=Video.Visibility.PUBLIC,
        )
        self.private_video = Video.objects.create(
            owner=self.owner, title='Star Wars Behind The Scenes (privé)', status=Video.Status.READY,
            visibility=Video.Visibility.PRIVATE,
        )
        self.public_live = LiveStream.objects.create(
            owner=self.owner, title='Star Wars Watch Party', visibility=LiveStream.Visibility.PUBLIC,
        )
        self.private_live = LiveStream.objects.create(
            owner=self.owner, title='Star Wars Private Live', visibility=LiveStream.Visibility.PRIVATE,
        )

    def test_search_is_public_and_unauthenticated(self):
        response = self.client.get(reverse('search:global-search'), {'q': 'Star Wars'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_returns_results_across_all_types(self):
        response = self.client.get(reverse('search:global-search'), {'q': 'Star Wars'})
        self.assertEqual(len(response.data['movies']), 1)
        self.assertEqual(len(response.data['posts']), 1)
        self.assertEqual(len(response.data['videos']), 1)
        self.assertEqual(len(response.data['live_streams']), 1)

    def test_search_excludes_private_content(self):
        response = self.client.get(reverse('search:global-search'), {'q': 'Star Wars'})
        video_titles = {v['title'] for v in response.data['videos']}
        live_titles = {live['title'] for live in response.data['live_streams']}
        self.assertNotIn('Star Wars Behind The Scenes (privé)', video_titles)
        self.assertNotIn('Star Wars Private Live', live_titles)

    def test_search_empty_query_returns_empty_results(self):
        response = self.client.get(reverse('search:global-search'), {'q': ''})
        self.assertEqual(response.data['movies'], [])
        self.assertEqual(response.data['videos'], [])

    def test_search_no_match_returns_empty_lists(self):
        response = self.client.get(reverse('search:global-search'), {'q': 'nonexistent-term-xyz'})
        self.assertEqual(response.data['movies'], [])
