from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from subscriptions import services
from subscriptions.models import Plan, Subscription


def _make_plan(**kwargs):
    defaults = {
        'name': 'Premium', 'slug': 'premium', 'tier': Plan.Tier.PREMIUM,
        'price': '9.99', 'currency': 'XOF', 'billing_period': Plan.BillingPeriod.MONTHLY,
        'trial_days': 0, 'is_active': True,
    }
    defaults.update(kwargs)
    return Plan.objects.create(**defaults)


class PlanCatalogTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='S3curePass!23', role=User.Role.ADMIN)
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.active_plan = _make_plan()
        self.inactive_plan = _make_plan(name='Old Plan', slug='old-plan', is_active=False)

    def test_public_plan_list_only_shows_active_plans(self):
        response = self.client.get(reverse('subscriptions:plan-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {p['name'] for p in response.data['results']}
        self.assertEqual(names, {'Premium'})

    def test_plain_user_cannot_create_plan(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('subscriptions:plan-admin-list'), {
            'name': 'VIP', 'slug': 'vip', 'tier': 'vip', 'price': '19.99', 'billing_period': 'monthly',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_plan(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('subscriptions:plan-admin-list'), {
            'name': 'VIP', 'slug': 'vip', 'tier': 'vip', 'price': '19.99', 'billing_period': 'monthly',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Plan.objects.filter(slug='vip').exists())


class SubscribeFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.user)

    def test_subscribe_to_plan_without_trial_is_pending_payment(self):
        plan = _make_plan()
        response = self.client.post(reverse('subscriptions:subscribe'), {'plan_id': str(plan.id)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['status'], 'pending')

    def test_subscribe_to_plan_with_trial_activates_trialing_immediately(self):
        plan = _make_plan(trial_days=7)
        response = self.client.post(reverse('subscriptions:subscribe'), {'plan_id': str(plan.id)})
        self.assertEqual(response.data['status'], 'trialing')
        subscription = Subscription.objects.get(user=self.user)
        self.assertTrue(subscription.is_active_now)

    def test_cannot_subscribe_twice_while_one_is_pending(self):
        plan = _make_plan()
        self.client.post(reverse('subscriptions:subscribe'), {'plan_id': str(plan.id)})
        response = self.client.post(reverse('subscriptions:subscribe'), {'plan_id': str(plan.id)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subscribe_rejects_inactive_plan(self):
        plan = _make_plan(is_active=False)
        response = self.client.post(reverse('subscriptions:subscribe'), {'plan_id': str(plan.id)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_my_subscription_returns_404_when_none(self):
        response = self.client.get(reverse('subscriptions:my-subscription'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_stops_auto_renew_but_keeps_access_until_period_end(self):
        plan = _make_plan(trial_days=7)
        self.client.post(reverse('subscriptions:subscribe'), {'plan_id': str(plan.id)})

        response = self.client.post(reverse('subscriptions:cancel'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['auto_renew'])

        subscription = Subscription.objects.get(user=self.user)
        self.assertTrue(subscription.is_active_now)
        self.assertEqual(subscription.status, Subscription.Status.TRIALING)


class SubscriptionServiceTests(APITestCase):
    def test_activate_subscription_sets_full_billing_period(self):
        user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        plan = _make_plan(billing_period=Plan.BillingPeriod.YEARLY)
        subscription = services.start_subscription(user, plan)

        services.activate_subscription(subscription)

        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertGreater(subscription.current_period_end, timezone.now() + timezone.timedelta(days=300))

    def test_is_active_now_false_after_period_end(self):
        user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        plan = _make_plan()
        subscription = Subscription.objects.create(
            user=user, plan=plan, status=Subscription.Status.ACTIVE,
            current_period_end=timezone.now() - timezone.timedelta(days=1),
        )
        self.assertFalse(subscription.is_active_now)
