"""Logique métier des abonnements : démarrage, activation, annulation, expiration."""
from datetime import timedelta

from django.utils import timezone

from subscriptions.models import Plan, Subscription

BILLING_DELTAS = {
    Plan.BillingPeriod.WEEKLY: timedelta(weeks=1),
    Plan.BillingPeriod.MONTHLY: timedelta(days=30),
    Plan.BillingPeriod.YEARLY: timedelta(days=365),
}


def billing_delta(period):
    return BILLING_DELTAS.get(period, timedelta(days=30))


def start_subscription(user, plan):
    """Crée un abonnement : en essai gratuit immédiat si le plan en propose un, sinon en attente de paiement."""
    now = timezone.now()
    if plan.trial_days > 0:
        return Subscription.objects.create(
            user=user, plan=plan, status=Subscription.Status.TRIALING,
            trial_end=now + timedelta(days=plan.trial_days),
            current_period_start=now,
            current_period_end=now + timedelta(days=plan.trial_days),
        )
    return Subscription.objects.create(
        user=user, plan=plan, status=Subscription.Status.PENDING, current_period_start=now,
    )


def activate_subscription(subscription):
    """Active (ou renouvelle) l'abonnement pour un cycle de facturation complet, typiquement après paiement."""
    now = timezone.now()
    subscription.status = Subscription.Status.ACTIVE
    subscription.current_period_start = now
    subscription.current_period_end = now + billing_delta(subscription.plan.billing_period)
    subscription.save(update_fields=['status', 'current_period_start', 'current_period_end'])
    return subscription


def cancel_subscription(subscription):
    """Désactive le renouvellement automatique ; l'accès reste valide jusqu'à la fin de la période en cours."""
    subscription.auto_renew = False
    subscription.canceled_at = timezone.now()
    subscription.save(update_fields=['auto_renew', 'canceled_at'])
    return subscription
