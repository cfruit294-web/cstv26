"""Client pour l'API OMDb (http://www.omdbapi.com/) : recherche et fiches détaillées."""
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.db.models import Q

RECOMMENDATIONS_LIMIT = 12


class OmdbError(Exception):
    """Levée lorsque l'API OMDb renvoie une erreur métier ou est injoignable."""


def _request(params):
    if not settings.OMDB_API_KEY:
        raise OmdbError("OMDB_API_KEY n'est pas configurée sur le serveur.")

    try:
        response = requests.get(
            settings.OMDB_BASE_URL,
            params={**params, 'apikey': settings.OMDB_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OmdbError(f'Impossible de contacter OMDb : {exc}') from exc

    data = response.json()
    if data.get('Response') == 'False':
        raise OmdbError(data.get('Error', 'Erreur OMDb inconnue.'))
    return data


def fetch_by_imdb_id(imdb_id):
    return _request({'i': imdb_id, 'plot': 'full'})


def fetch_by_title(title, year=None):
    params = {'t': title, 'plot': 'full'}
    if year:
        params['y'] = year
    return _request(params)


def search(q, page=1):
    data = _request({'s': q, 'page': page})
    return {
        'results': data.get('Search', []),
        'total_results': int(data.get('totalResults', 0)),
        'page': page,
    }


def _parse_runtime(raw_runtime):
    if not raw_runtime or raw_runtime == 'N/A':
        return None
    digits = ''.join(ch for ch in raw_runtime if ch.isdigit())
    return int(digits) if digits else None


def _parse_rating(raw_rating):
    if not raw_rating or raw_rating == 'N/A':
        return None
    try:
        return Decimal(raw_rating)
    except InvalidOperation:
        return None


def to_movie_fields(data):
    """Convertit une fiche détaillée OMDb en champs prêts pour le modèle Movie."""
    poster = data.get('Poster')
    return {
        'imdb_id': data['imdbID'],
        'title': data.get('Title', ''),
        'year': data.get('Year', ''),
        'type': data.get('Type', 'movie'),
        'rated': data.get('Rated', ''),
        'runtime_minutes': _parse_runtime(data.get('Runtime')),
        'genre': data.get('Genre', ''),
        'director': data.get('Director', ''),
        'actors': data.get('Actors', ''),
        'plot': data.get('Plot', ''),
        'poster_url': poster if poster and poster != 'N/A' else '',
        'imdb_rating': _parse_rating(data.get('imdbRating')),
        'raw_data': data,
    }


def get_recommended_movies(movie, limit=RECOMMENDATIONS_LIMIT):
    """Films à recommander sous une fiche : même genre en priorité, puis mêmes acteurs,
    puis même type ; le tout trié par note IMDb décroissante, sans jamais renvoyer `movie`.
    """
    from catalog.models import Movie

    genres = [g.strip() for g in movie.genre.split(',') if g.strip()]
    actors = [a.strip() for a in movie.actors.split(',') if a.strip()]

    genre_query = Q()
    for genre in genres:
        genre_query |= Q(genre__icontains=genre)

    actor_query = Q()
    for actor in actors:
        actor_query |= Q(actors__icontains=actor)

    base = Movie.objects.exclude(id=movie.id)
    scored = base.filter(genre_query) if genres else Movie.objects.none()
    if scored.count() < limit and actors:
        scored = base.filter(genre_query | actor_query) if genres else base.filter(actor_query)
    if scored.count() < limit:
        scored = base.filter(Q(id__in=scored.values('id')) | Q(type=movie.type))

    return list(scored.order_by('-imdb_rating', '-created_at')[:limit])
