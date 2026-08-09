from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Plan(BaseModel):
    """Formule d'abonnement proposée aux utilisateurs (Basic, Premium, VIP, Entreprise...)."""

    class Tier(models.TextChoices):
        BASIC = 'basic', 'Basic'
        PREMIUM = 'premium', 'Premium'
        VIP = 'vip', 'VIP'
        ENTERPRISE = 'enterprise', 'Entreprise'

    class BillingPeriod(models.TextChoices):
        WEEKLY = 'weekly', 'Hebdomadaire'
        MONTHLY = 'monthly', 'Mensuel'
        YEARLY = 'yearly', 'Annuel'

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.BASIC)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    billing_period = models.CharField(max_length=10, choices=BillingPeriod.choices, default=BillingPeriod.MONTHLY)
    trial_days = models.PositiveIntegerField(default=0)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f'{self.name} ({self.get_billing_period_display()})'


class Subscription(BaseModel):
    """Abonnement d'un utilisateur à une formule, avec suivi du cycle de facturation."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente de paiement'
        TRIALING = 'trialing', "Période d'essai"
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Paiement en retard'
        CANCELED = 'canceled', 'Annulée'
        EXPIRED = 'expired', 'Expirée'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} -> {self.plan.name} ({self.status})'

    @property
    def is_active_now(self):
        if self.status not in (self.Status.ACTIVE, self.Status.TRIALING):
            return False
        if self.current_period_end and timezone.now() > self.current_period_end:
            return False
        return True
