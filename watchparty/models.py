from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel
from videos.models import Video


class WatchParty(BaseModel):
    """Séance de visionnage groupé : un hôte choisit une vidéo publique et une heure, d'autres rejoignent."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Planifiée'
        LIVE = 'live', 'En cours'
        ENDED = 'ended', 'Terminée'
        CANCELED = 'canceled', 'Annulée'

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_watch_parties')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='watch_parties')
    title = models.CharField(max_length=255, blank=True)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)

    # État de lecture partagé, synchronisé en temps réel via WebSocket (voir watchparty.consumers).
    playback_position_seconds = models.FloatField(default=0)
    is_playing = models.BooleanField(default=False)
    playback_updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_at']
        verbose_name_plural = 'watch parties'

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        return self.title or self.video.title

    @property
    def current_position_seconds(self):
        if not self.is_playing:
            return self.playback_position_seconds
        elapsed = (timezone.now() - self.playback_updated_at).total_seconds()
        return self.playback_position_seconds + max(elapsed, 0)


class WatchPartyMembership(BaseModel):
    """Demande/acceptation de participation d'un utilisateur à une séance (hors hôte, géré séparément)."""

    class Role(models.TextChoices):
        MEMBER = 'member', 'Membre'
        MODERATOR = 'moderator', 'Modérateur'

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACCEPTED = 'accepted', 'Acceptée'
        REJECTED = 'rejected', 'Refusée'

    party = models.ForeignKey(WatchParty, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watch_party_memberships')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['party', 'user'], name='unique_watchparty_membership'),
        ]

    def __str__(self):
        return f'{self.user.email} @ {self.party_id} ({self.status})'


class WatchPartyChatMessage(BaseModel):
    """Message de chat associé à une séance (historique persistant, diffusé en temps réel via WebSocket)."""

    party = models.ForeignKey(WatchParty, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watch_party_chat_messages')
    message = models.CharField(max_length=500)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.email}: {self.message[:30]}'
