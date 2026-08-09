from unittest.mock import Mock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import Movie
from catalog.services import OmdbError, to_movie_fields

OMDB_DETAIL_RESPONSE = {
    'Title': 'Guardians of the Galaxy Vol. 2',
    'Year': '2017',
    'Rated': 'PG-13',
    'Runtime': '136 min',
    'Genre': 'Action, Adventure, Comedy',
    'Director': 'James Gunn',
    'Actors': 'Chris Pratt, Zoe Saldaña, Dave Bautista',
    'Plot': 'The Guardians struggle to keep together as a team.',
    'Poster': 'https://example.com/poster.jpg',
    'imdbRating': '7.6',
    'imdbID': 'tt3896198',
    'Type': 'movie',
    'Response': 'True',
}

OMDB_SEARCH_RESPONSE = {
    'Search': [{'Title': 'Guardians of the Galaxy Vol. 2', 'Year': '2017', 'imdbID': 'tt3896198', 'Type': 'movie'}],
    'totalResults': '1',
    'Response': 'True',
}

OMDB_NOT_FOUND_RESPONSE = {'Response': 'False', 'Error': 'Movie not found!'}


def _mock_response(json_data, status_code=200):
    mock_resp = Mock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = Mock()
    return mock_resp


class OmdbFieldMappingTests(APITestCase):
    def test_to_movie_fields_parses_runtime_and_rating(self):
        fields = to_movie_fields(OMDB_DETAIL_RESPONSE)
        self.assertEqual(fields['runtime_minutes'], 136)
        self.assertEqual(str(fields['imdb_rating']), '7.6')
        self.assertEqual(fields['imdb_id'], 'tt3896198')

    def test_to_movie_fields_handles_missing_values(self):
        data = {**OMDB_DETAIL_RESPONSE, 'Runtime': 'N/A', 'imdbRating': 'N/A', 'Poster': 'N/A'}
        fields = to_movie_fields(data)
        self.assertIsNone(fields['runtime_minutes'])
        self.assertIsNone(fields['imdb_rating'])
        self.assertEqual(fields['poster_url'], '')


class MovieImportViewTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email='creator@example.com', password='S3curePass!23', role=User.Role.CREATOR,
        )
        self.viewer = User.objects.create_user(email='viewer@example.com', password='S3curePass!23')

    def _login(self, user):
        self.client.force_authenticate(user=user)

    @patch('catalog.services.requests.get')
    def test_creator_can_import_movie_by_imdb_id(self, mock_get):
        mock_get.return_value = _mock_response(OMDB_DETAIL_RESPONSE)
        self._login(self.creator)

        response = self.client.post(reverse('catalog:movie-import'), {'imdb_id': 'tt3896198'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['title'], 'Guardians of the Galaxy Vol. 2')
        movie = Movie.objects.get(imdb_id='tt3896198')
        self.assertEqual(movie.imported_by, self.creator)

    @patch('catalog.services.requests.get')
    def test_reimporting_same_movie_updates_existing_row(self, mock_get):
        mock_get.return_value = _mock_response(OMDB_DETAIL_RESPONSE)
        self._login(self.creator)

        self.client.post(reverse('catalog:movie-import'), {'imdb_id': 'tt3896198'})
        self.client.post(reverse('catalog:movie-import'), {'imdb_id': 'tt3896198'})

        self.assertEqual(Movie.objects.filter(imdb_id='tt3896198').count(), 1)

    @patch('catalog.services.requests.get')
    def test_import_returns_502_when_omdb_reports_not_found(self, mock_get):
        mock_get.return_value = _mock_response(OMDB_NOT_FOUND_RESPONSE)
        self._login(self.creator)

        response = self.client.post(reverse('catalog:movie-import'), {'imdb_id': 'tt0000000'})

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Movie not found', response.data['detail'])

    def test_import_requires_imdb_id_or_title(self):
        self._login(self.creator)
        response = self.client.post(reverse('catalog:movie-import'), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('catalog.services.requests.get')
    def test_plain_user_cannot_import(self, mock_get):
        self._login(self.viewer)
        response = self.client.post(reverse('catalog:movie-import'), {'imdb_id': 'tt3896198'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_get.assert_not_called()


class OmdbSearchViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='viewer@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.user)

    @patch('catalog.services.requests.get')
    def test_search_returns_omdb_results_without_persisting(self, mock_get):
        mock_get.return_value = _mock_response(OMDB_SEARCH_RESPONSE)

        response = self.client.get(reverse('catalog:omdb-search'), {'q': 'Guardians'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_results'], 1)
        self.assertEqual(Movie.objects.count(), 0)

    def test_search_requires_query_param(self):
        response = self.client.get(reverse('catalog:omdb-search'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MovieCatalogBrowseTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='viewer@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(**{k: v for k, v in to_movie_fields(OMDB_DETAIL_RESPONSE).items()})

    def test_list_movies(self):
        response = self.client.get(reverse('catalog:movie-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_list_movies_filtered_by_query(self):
        response = self.client.get(reverse('catalog:movie-list'), {'q': 'nonexistent'})
        self.assertEqual(response.data['count'], 0)

    def test_retrieve_movie_detail(self):
        response = self.client.get(reverse('catalog:movie-detail', args=[self.movie.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['imdb_id'], 'tt3896198')
