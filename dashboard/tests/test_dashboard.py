from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from community.models import Post
from payments.models import Payment
from subscriptions import services as subscription_services
from subscriptions.models import Plan
from videos.models import Video


class DashboardOverviewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='S3curePass!23', role=User.Role.ADMIN)
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')

    def test_plain_user_cannot_access_dashboard(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_gets_overview_with_expected_sections(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for section in ('users', 'subscriptions', 'revenue', 'videos', 'live', 'community', 'messaging'):
            self.assertIn(section, response.data)

    def test_user_counts_reflect_database_state(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.data['users']['total'], 2)

    def test_revenue_only_counts_successful_payments(self):
        Payment.objects.create(user=self.user, transaction_id='ok1', amount='100.00', currency='XOF', status=Payment.Status.SUCCESS)
        Payment.objects.create(user=self.user, transaction_id='ok2', amount='50.00', currency='XOF', status=Payment.Status.SUCCESS)
        Payment.objects.create(user=self.user, transaction_id='failed1', amount='999.00', currency='XOF', status=Payment.Status.FAILED)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        # SQLite n'agrège pas les DecimalField avec une échelle stable (150 vs 150.00) ;
        # on compare donc la valeur numérique plutôt que la représentation texte exacte.
        self.assertEqual(Decimal(response.data['revenue']['total']), Decimal('150.00'))
        self.assertEqual(response.data['revenue']['successful_payments'], 2)

    def test_subscription_counts_active_and_trialing(self):
        plan = Plan.objects.create(
            name='Premium', slug='premium', price='10.00', currency='XOF',
            billing_period=Plan.BillingPeriod.MONTHLY, trial_days=7,
        )
        subscription_services.start_subscription(self.user, plan)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.data['subscriptions']['active'], 1)

    def test_community_and_video_counts(self):
        Post.objects.create(author=self.user, content='Salut')
        Video.objects.create(owner=self.user, title='Clip', status=Video.Status.READY)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.data['community']['posts'], 1)
        self.assertEqual(response.data['videos']['ready'], 1)
