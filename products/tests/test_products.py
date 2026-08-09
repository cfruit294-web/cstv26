from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from products.models import Category, Product


class CategoryTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='S3curePass!23', role=User.Role.ADMIN)
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')

    def test_public_can_list_categories(self):
        Category.objects.create(name='Livres', slug='livres')
        response = self.client.get(reverse('products:category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_plain_user_cannot_create_category(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('products:category-admin-list'), {'name': 'Livres', 'slug': 'livres'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_category(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('products:category-admin-list'), {'name': 'Livres', 'slug': 'livres'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ProductCreationTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.viewer = User.objects.create_user(email='viewer@example.com', password='S3curePass!23')

    def test_seller_can_create_digital_product(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(reverse('products:product-create'), {
            'name': 'Ebook', 'slug': 'ebook', 'product_type': 'digital', 'price': '9.99', 'currency': 'XOF',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        product = Product.objects.get(slug='ebook')
        self.assertEqual(product.seller, self.seller)
        self.assertTrue(product.is_in_stock)

    def test_plain_user_cannot_create_product(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(reverse('products:product-create'), {
            'name': 'Ebook', 'slug': 'ebook', 'product_type': 'digital', 'price': '9.99',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_physical_product_requires_stock_quantity(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(reverse('products:product-create'), {
            'name': 'T-shirt', 'slug': 't-shirt', 'product_type': 'physical', 'price': '19.99',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_physical_product_with_stock_is_created(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(reverse('products:product-create'), {
            'name': 'T-shirt', 'slug': 't-shirt', 'product_type': 'physical', 'price': '19.99', 'stock_quantity': 10,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ProductCatalogTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.category = Category.objects.create(name='Livres', slug='livres')
        self.active = Product.objects.create(
            seller=self.seller, name='Ebook actif', slug='ebook-actif', product_type=Product.ProductType.DIGITAL,
            price='5.00', category=self.category, is_active=True,
        )
        self.inactive = Product.objects.create(
            seller=self.seller, name='Ebook inactif', slug='ebook-inactif', product_type=Product.ProductType.DIGITAL,
            price='5.00', is_active=False,
        )

    def test_public_list_hides_inactive_products(self):
        response = self.client.get(reverse('products:product-list'))
        names = {p['name'] for p in response.data['results']}
        self.assertEqual(names, {'Ebook actif'})

    def test_filter_by_category(self):
        response = self.client.get(reverse('products:product-list'), {'category': 'livres'})
        self.assertEqual(response.data['count'], 1)

    def test_search_by_name(self):
        response = self.client.get(reverse('products:product-list'), {'q': 'actif'})
        self.assertEqual(response.data['count'], 1)

    def test_seller_sees_own_inactive_products_via_mine(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(reverse('products:product-mine'))
        self.assertEqual(response.data['count'], 2)


class ProductOwnershipTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.other_seller = User.objects.create_user(
            email='other@example.com', password='S3curePass!23', role=User.Role.BUSINESS,
        )
        self.product = Product.objects.create(
            seller=self.seller, name='Ebook', slug='ebook', product_type=Product.ProductType.DIGITAL, price='5.00',
        )

    def test_owner_can_update_product(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(reverse('products:product-manage', args=[self.product.id]), {'price': '7.50'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_seller_cannot_update_product(self):
        self.client.force_authenticate(user=self.other_seller)
        response = self.client.patch(reverse('products:product-manage', args=[self.product.id]), {'price': '7.50'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
