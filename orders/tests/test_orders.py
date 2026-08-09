import tempfile
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from orders.models import Order
from orders.services import mark_order_paid
from payments.models import Payment
from products.models import Product

CINETPAY_INIT_SUCCESS = {
    'code': '201',
    'message': 'CREATED',
    'data': {'payment_token': 'tok_123', 'payment_url': 'https://checkout.cinetpay.com/payment/tok_123'},
}


def _mock_response(json_data, status_code=200):
    mock_resp = Mock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = Mock()
    return mock_resp


class OrderCreationTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.buyer = User.objects.create_user(email='buyer@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.buyer)

        self.digital = Product.objects.create(
            seller=self.seller, name='Ebook', slug='ebook', product_type=Product.ProductType.DIGITAL, price='10.00',
        )
        self.physical = Product.objects.create(
            seller=self.seller, name='T-shirt', slug='t-shirt', product_type=Product.ProductType.PHYSICAL,
            price='20.00', stock_quantity=2,
        )

    def test_create_order_computes_total_and_creates_items(self):
        response = self.client.post(reverse('orders:order-create'), {
            'items': [
                {'product_id': str(self.digital.id), 'quantity': 1},
                {'product_id': str(self.physical.id), 'quantity': 2},
            ],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['total_amount'], '50.00')
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(response.data['status'], 'pending')

    def test_create_order_rejects_insufficient_stock(self):
        response = self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.physical.id), 'quantity': 5}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_rejects_empty_items(self):
        response = self.client.post(reverse('orders:order-create'), {'items': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_rejects_inactive_product(self):
        self.digital.is_active = False
        self.digital.save(update_fields=['is_active'])
        response = self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.digital.id), 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrderPaidStockTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.buyer = User.objects.create_user(email='buyer@example.com', password='S3curePass!23')
        self.physical = Product.objects.create(
            seller=self.seller, name='T-shirt', slug='t-shirt', product_type=Product.ProductType.PHYSICAL,
            price='20.00', stock_quantity=5,
        )

    def test_mark_order_paid_decrements_physical_stock(self):
        self.client.force_authenticate(user=self.buyer)
        create_response = self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.physical.id), 'quantity': 3}],
        }, format='json')
        order = Order.objects.get(id=create_response.data['id'])

        mark_order_paid(order)

        self.physical.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.physical.stock_quantity, 2)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertIsNotNone(order.paid_at)

    def test_mark_order_paid_notifies_buyer(self):
        self.client.force_authenticate(user=self.buyer)
        create_response = self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.physical.id), 'quantity': 1}],
        }, format='json')
        order = Order.objects.get(id=create_response.data['id'])

        mark_order_paid(order)

        from notifications.models import Notification
        notification = Notification.objects.get(recipient=self.buyer)
        self.assertEqual(notification.category, Notification.Category.ORDER)

    def test_mark_order_paid_is_idempotent(self):
        self.client.force_authenticate(user=self.buyer)
        create_response = self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.physical.id), 'quantity': 1}],
        }, format='json')
        order = Order.objects.get(id=create_response.data['id'])

        mark_order_paid(order)
        mark_order_paid(order)

        self.physical.refresh_from_db()
        self.assertEqual(self.physical.stock_quantity, 4)


@override_settings(CINETPAY_API_KEY='test-key', CINETPAY_SITE_ID='test-site', MEDIA_ROOT=tempfile.mkdtemp())
class OrderCheckoutTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.buyer = User.objects.create_user(email='buyer@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.buyer)

        self.digital = Product.objects.create(
            seller=self.seller, name='Ebook', slug='ebook', product_type=Product.ProductType.DIGITAL, price='10.00',
            digital_file=SimpleUploadedFile('ebook.pdf', b'%PDF-1.4 fake content', content_type='application/pdf'),
        )
        response = self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.digital.id), 'quantity': 1}],
        }, format='json')
        self.order = Order.objects.get(id=response.data['id'])

    @patch('payments.services.requests.post')
    def test_checkout_creates_payment_linked_to_order(self, mock_post):
        mock_post.return_value = _mock_response(CINETPAY_INIT_SUCCESS)

        response = self.client.post(reverse('orders:order-checkout', args=[self.order.id]))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.amount, self.order.total_amount)

    def test_stranger_cannot_checkout_someone_elses_order(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(reverse('orders:order-checkout', args=[self.order.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('payments.services.requests.post')
    def test_notify_marks_order_paid_and_grants_digital_download(self, mock_post):
        mock_post.return_value = _mock_response(CINETPAY_INIT_SUCCESS)
        checkout = self.client.post(reverse('orders:order-checkout', args=[self.order.id]))
        transaction_id = checkout.data['transaction_id']

        download_before = self.client.get(
            reverse('orders:order-download', args=[self.order.id, self.digital.id]),
        )
        self.assertEqual(download_before.status_code, status.HTTP_403_FORBIDDEN)

        mock_post.return_value = _mock_response({'code': '00', 'data': {'status': 'ACCEPTED'}})
        notify_response = self.client.post(reverse('payments:cinetpay-notify'), {'cpm_trans_id': transaction_id})
        self.assertEqual(notify_response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)

        download_after = self.client.get(
            reverse('orders:order-download', args=[self.order.id, self.digital.id]),
        )
        self.assertEqual(download_after.status_code, status.HTTP_200_OK)
        self.assertIn('download_url', download_after.data)


class OrderListingTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.buyer = User.objects.create_user(email='buyer@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        self.digital = Product.objects.create(
            seller=self.seller, name='Ebook', slug='ebook', product_type=Product.ProductType.DIGITAL, price='10.00',
        )

    def test_user_only_sees_own_orders(self):
        self.client.force_authenticate(user=self.buyer)
        self.client.post(reverse('orders:order-create'), {
            'items': [{'product_id': str(self.digital.id), 'quantity': 1}],
        }, format='json')

        self.client.force_authenticate(user=self.other)
        response = self.client.get(reverse('orders:order-list'))
        self.assertEqual(response.data['count'], 0)
