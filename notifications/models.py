from django.conf import settings
from django.db import models

from core.models import BaseModel


class Notification(BaseModel):
    class Category(models.TextChoices):
        INFO = 'info', 'Information'
        COMMENT = 'comment', 'Commentaire'
        ORDER = 'order', 'Commande'
        PAYMENT = 'payment', 'Paiement'
        LIVE = 'live', 'Live'
        MESSAGE = 'message', 'Message'
        SYSTEM = 'system', 'Système'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.INFO)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.email}: {self.title}'
