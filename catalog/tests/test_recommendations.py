from django.urls import reverse
from rest_framework.test import APITestCase

from catalog.models import Movie
from catalog.services import get_recommended_movies


def _movie(**kwargs):
    defaults = {'imdb_id': f'tt{Movie.objects.count() + 1:07d}', 'title': 'Film', 'type': Movie.Type.MOVIE}
    defaults.update(kwargs)
    return Movie.objects.create(**defaults)


class GetRecommendedMoviesTests(APITestCase):
    def test_prioritizes_same_genre(self):
        movie = _movie(title='Dune', genre='Sci-Fi, Adventure', actors='Timothée Chalamet')
        same_genre = _movie(title='Blade Runner', genre='Sci-Fi', actors='Harrison Ford')
        _movie(title='Comédie romantique', genre='Romance', actors='Personne')

        results = get_recommended_movies(movie)
        self.assertIn(same_genre, results)
        self.assertNotIn(movie, results)

    def test_excludes_the_movie_itself(self):
        movie = _movie(title='Dune', genre='Sci-Fi')
        results = get_recommended_movies(movie)
        self.assertNotIn(movie, results)

    def test_respects_limit(self):
        movie = _movie(title='Dune', genre='Sci-Fi')
        for i in range(15):
            _movie(title=f'Sci-Fi {i}', genre='Sci-Fi')

        results = get_recommended_movies(movie, limit=5)
        self.assertEqual(len(results), 5)

    def test_falls_back_to_same_type_when_no_genre_match(self):
        movie = _movie(title='Dune', genre='Sci-Fi', type=Movie.Type.MOVIE)
        other_type = _movie(title='Une série', genre='Comédie', type=Movie.Type.SERIES)
        same_type_no_genre = _movie(title='Autre film', genre='Comédie', type=Movie.Type.MOVIE)

        results = get_recommended_movies(movie)
        self.assertIn(same_type_no_genre, results)
        self.assertNotIn(other_type, results)


class MovieRecommendationsViewTests(APITestCase):
    def test_endpoint_returns_recommendations(self):
        movie = _movie(title='Dune', genre='Sci-Fi')
        same_genre = _movie(title='Blade Runner', genre='Sci-Fi')

        response = self.client.get(reverse('catalog:movie-recommendations', args=[movie.id]))
        titles = {m['title'] for m in response.data['results']}
        self.assertIn(same_genre.title, titles)
        self.assertNotIn(movie.title, titles)
