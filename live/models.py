import secrets

from django.conf import settings
from django.db import models

from core.models import BaseModel


def generate_stream_key():
    return secrets.token_urlsafe(24)


class LiveStream(BaseModel):
    """Live planifié/en cours, ingéré via RTMP par un serveur média externe (nginx-rtmp, MediaMTX...)."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Planifié'
        LIVE = 'live', 'En direct'
        ENDED = 'ended', 'Terminé'
        CANCELED = 'canceled', 'Annulé'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Privé'
        PREMIUM = 'premium', 'Premium'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='live_streams')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    stream_key = models.CharField(max_length=64, unique=True, default=generate_stream_key, editable=False)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    scheduled_duration_minutes = models.PositiveIntegerField(
        default=60, help_text="Durée estimée, utilisée pour l'affichage dans la grille de programmation.",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    replay_video = models.ForeignKey(
        'videos.Video', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_live_stream',
        help_text="Rediffusion VOD générée automatiquement à partir de l'enregistrement du live.",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def rtmp_ingest_url(self) -> str:
        return f'{settings.RTMP_INGEST_BASE_URL}/{self.stream_key}'

    @property
    def hls_playback_url(self) -> str:
        return f'{settings.HLS_PLAYBACK_BASE_URL}/{self.stream_key}/index.m3u8'


class LiveChatMessage(BaseModel):
    """Message de chat associé à un live (historique persistant, diffusé en temps réel via WebSocket)."""

    stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='live_chat_messages')
    message = models.CharField(max_length=500)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.email}: {self.message[:30]}'
