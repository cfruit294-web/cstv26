from django.conf import settings
from django.db import models

from core.models import BaseModel


class Movie(BaseModel):
    """Fiche film/série mise en cache localement à partir des données OMDb."""

    class Type(models.TextChoices):
        MOVIE = 'movie', 'Film'
        SERIES = 'series', 'Série'
        EPISODE = 'episode', 'Épisode'

    imdb_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    year = models.CharField(max_length=20, blank=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.MOVIE)
    rated = models.CharField(max_length=20, blank=True)
    runtime_minutes = models.PositiveIntegerField(null=True, blank=True)
    genre = models.CharField(max_length=255, blank=True)
    director = models.CharField(max_length=255, blank=True)
    actors = models.CharField(max_length=500, blank=True)
    plot = models.TextField(blank=True)
    poster_url = models.URLField(max_length=500, blank=True)
    imdb_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imported_movies',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.year})'
