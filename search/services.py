"""Recherche globale multi-modèles via l'ORM (interface stable, remplaçable par Elasticsearch plus tard).

Ne recherche que le contenu déjà public (mêmes règles de visibilité que les listes publiques
de chaque app), volontairement simple : pas d'exposition de contenu privé via la recherche globale.
"""
from catalog.models import Movie
from community.models import Post
from live.models import LiveStream
from products.models import Product
from videos.models import Video

RESULTS_PER_TYPE = 10


def global_search(query):
    query = (query or '').strip()
    if not query:
        return {'movies': [], 'videos': [], 'products': [], 'live_streams': [], 'posts': []}

    return {
        'movies': list(Movie.objects.filter(title__icontains=query)[:RESULTS_PER_TYPE]),
        'videos': list(Video.objects.filter(
            status=Video.Status.READY, visibility=Video.Visibility.PUBLIC, title__icontains=query,
        )[:RESULTS_PER_TYPE]),
        'products': list(Product.objects.filter(is_active=True, name__icontains=query)[:RESULTS_PER_TYPE]),
        'live_streams': list(
            LiveStream.objects.filter(visibility=LiveStream.Visibility.PUBLIC, title__icontains=query)
            .exclude(status=LiveStream.Status.CANCELED)[:RESULTS_PER_TYPE]
        ),
        'posts': list(Post.objects.filter(content__icontains=query)[:RESULTS_PER_TYPE]),
    }
