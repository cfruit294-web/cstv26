from django.conf import settings
from django.db import models

from catalog.models import Movie
from core.models import BaseModel


class WatchlistItem(BaseModel):
    """Film qu'un utilisateur a ajouté à « Ma liste »."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist_items')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='watchlist_items')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'movie'], name='unique_watchlist_item'),
        ]

    def __str__(self):
        return f'{self.user.email} · {self.movie.title}'


class WatchHistory(BaseModel):
    """Position de lecture d'un utilisateur sur une vidéo, pour permettre la reprise automatique."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watch_history')
    video = models.ForeignKey('videos.Video', on_delete=models.CASCADE, related_name='watch_history')
    position_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'video'], name='unique_watch_history_entry'),
        ]

    def __str__(self):
        return f'{self.user.email} · {self.video.title} ({self.position_seconds}s)'
