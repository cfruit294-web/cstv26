from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from payments.models import Payment
from subscriptions import services as subscription_services
from subscriptions.models import Plan, Subscription

CINETPAY_INIT_SUCCESS = {
    'code': '201',
    'message': 'CREATED',
    'data': {'payment_token': 'tok_123', 'payment_url': 'https://checkout.cinetpay.com/payment/tok_123'},
}

CINETPAY_INIT_FAILURE = {'code': '600', 'message': 'INVALID_APIKEY'}


def _mock_response(json_data, status_code=200):
    mock_resp = Mock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = Mock()
    return mock_resp


def _make_plan(**kwargs):
    defaults = {
        'name': 'Premium', 'slug': 'premium', 'tier': Plan.Tier.PREMIUM,
        'price': '5000', 'currency': 'XOF', 'billing_period': Plan.BillingPeriod.MONTHLY,
    }
    defaults.update(kwargs)
    return Plan.objects.create(**defaults)


@override_settings(CINETPAY_API_KEY='test-key', CINETPAY_SITE_ID='test-site')
class CheckoutViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.user)
        self.plan = _make_plan()
        self.subscription = subscription_services.start_subscription(self.user, self.plan)

    @patch('payments.services.requests.post')
    def test_checkout_creates_payment_and_returns_payment_url(self, mock_post):
        mock_post.return_value = _mock_response(CINETPAY_INIT_SUCCESS)

        response = self.client.post(reverse('payments:checkout'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['payment_url'], 'https://checkout.cinetpay.com/payment/tok_123')
        payment = Payment.objects.get(user=self.user)
        self.assertEqual(payment.subscription, self.subscription)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    @patch('payments.services.requests.post')
    def test_checkout_returns_502_when_cinetpay_rejects(self, mock_post):
        mock_post.return_value = _mock_response(CINETPAY_INIT_FAILURE)

        response = self.client.post(reverse('payments:checkout'))

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(Payment.objects.exists())

    def test_checkout_without_pending_subscription_fails(self):
        self.subscription.delete()
        response = self.client.post(reverse('payments:checkout'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(CINETPAY_API_KEY='test-key', CINETPAY_SITE_ID='test-site')
class CinetPayNotifyViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.plan = _make_plan()
        self.subscription = subscription_services.start_subscription(self.user, self.plan)
        self.payment = Payment.objects.create(
            user=self.user, subscription=self.subscription, transaction_id='SFabc123',
            amount=self.plan.price, currency=self.plan.currency,
        )

    @patch('payments.services.requests.post')
    def test_notify_activates_subscription_on_accepted(self, mock_post):
        mock_post.return_value = _mock_response({'code': '00', 'data': {'status': 'ACCEPTED'}})

        response = self.client.post(reverse('payments:cinetpay-notify'), {'cpm_trans_id': 'SFabc123'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCESS)
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)
        self.assertIsNotNone(self.subscription.current_period_end)

    @patch('payments.services.requests.post')
    def test_notify_marks_failed_on_refused(self, mock_post):
        mock_post.return_value = _mock_response({'code': '00', 'data': {'status': 'REFUSED'}})

        self.client.post(reverse('payments:cinetpay-notify'), {'cpm_trans_id': 'SFabc123'})

        self.payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.subscription.status, Subscription.Status.PENDING)

    def test_notify_unknown_transaction_returns_404(self):
        response = self.client.post(reverse('payments:cinetpay-notify'), {'cpm_trans_id': 'unknown'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notify_requires_transaction_id(self):
        response = self.client.post(reverse('payments:cinetpay-notify'), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PaymentListingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        self.admin = User.objects.create_user(email='admin@example.com', password='S3curePass!23', role=User.Role.ADMIN)
        self.payment = Payment.objects.create(
            user=self.user, transaction_id='SFone', amount='10.00', currency='XOF',
        )
        Payment.objects.create(user=self.other, transaction_id='SFtwo', amount='20.00', currency='XOF')

    def test_user_only_sees_own_payments(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('payments:payment-list'))
        self.assertEqual(response.data['count'], 1)

    def test_admin_sees_all_payments(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payments:payment-list'))
        self.assertEqual(response.data['count'], 2)

    def test_user_cannot_retrieve_others_payment(self):
        self.client.force_authenticate(user=self.user)
        other_payment = Payment.objects.get(transaction_id='SFtwo')
        response = self.client.get(reverse('payments:payment-detail', args=[other_payment.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
