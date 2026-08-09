from django.conf import settings
from django.db import models

from catalog.models import Movie
from core.models import BaseModel


def source_upload_path(instance, filename):
    return f'videos/source/{instance.id}/{filename}'


def subtitle_upload_path(instance, filename):
    # Nom fixe (langue) plutôt que le nom du fichier uploadé : la route de service protégée
    # (ProtectedSubtitleFileView) reconstruit ce chemin à partir de video_id + language seuls.
    return f'videos/subtitles/{instance.video_id}/{instance.language}.vtt'


class Video(BaseModel):
    """Vidéo uploadée par un créateur, transcodée en HLS multi-résolution par Celery/FFmpeg."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        PROCESSING = 'processing', 'En traitement'
        READY = 'ready', 'Disponible'
        FAILED = 'failed', 'Échec'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Privé'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='videos')
    movie = models.ForeignKey(
        Movie, on_delete=models.SET_NULL, null=True, blank=True, related_name='videos',
        help_text='Fiche catalogue (OMDb) associée, le cas échéant.',
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    source_file = models.FileField(upload_to=source_upload_path)
    thumbnail = models.ImageField(upload_to='videos/thumbnails/', blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    hls_master_playlist = models.CharField(max_length=500, blank=True)
    renditions = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Subtitle(BaseModel):
    """Piste de sous-titres (WebVTT) d'une vidéo, dans une langue donnée."""

    class Language(models.TextChoices):
        FR = 'fr', 'Français'
        EN = 'en', 'Anglais'

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='subtitles')
    language = models.CharField(max_length=5, choices=Language.choices)
    file = models.FileField(upload_to=subtitle_upload_path)

    class Meta:
        ordering = ['language']
        constraints = [
            models.UniqueConstraint(fields=['video', 'language'], name='unique_subtitle_language_per_video'),
        ]

    def __str__(self):
        return f'{self.video.title} ({self.get_language_display()})'
