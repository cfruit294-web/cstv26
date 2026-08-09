from django.conf import settings
from django.db import models

from core.models import BaseModel


class Payment(BaseModel):
    """Transaction de paiement (abonnement, location, don...) via un prestataire externe."""

    class Provider(models.TextChoices):
        CINETPAY = 'cinetpay', 'CinetPay'

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SUCCESS = 'success', 'Réussi'
        FAILED = 'failed', 'Échoué'
        CANCELED = 'canceled', 'Annulé'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(
        'subscriptions.Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments',
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments',
    )
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.CINETPAY)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_url = models.URLField(max_length=500, blank=True)
    description = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_id} ({self.status})'
