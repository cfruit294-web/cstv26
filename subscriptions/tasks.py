"""Tâches planifiées de gestion du cycle de vie des abonnements."""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from subscriptions.models import Subscription

PAST_DUE_GRACE_PERIOD = timedelta(days=3)


@shared_task
def expire_subscriptions():
    """Fait avancer les abonnements dont la période de facturation est dépassée.

    - active/trialing arrivés à échéance -> past_due (renouvellement auto attendu) ou expired (annulé).
    - past_due depuis plus que le délai de grâce -> expired.
    """
    now = timezone.now()

    lapsed = Subscription.objects.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING],
        current_period_end__lt=now,
    )
    lapsed.filter(auto_renew=True).update(status=Subscription.Status.PAST_DUE)
    lapsed.filter(auto_renew=False).update(status=Subscription.Status.EXPIRED)

    Subscription.objects.filter(
        status=Subscription.Status.PAST_DUE,
        current_period_end__lt=now - PAST_DUE_GRACE_PERIOD,
    ).update(status=Subscription.Status.EXPIRED)
