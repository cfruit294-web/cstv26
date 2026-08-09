from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def test_health_check_is_public_and_ok(self):
        response = self.client.get(reverse('core:health-check'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertIn('timestamp', response.data)


class ExceptionHandlerFormatTests(APITestCase):
    def test_validation_error_is_normalized_to_detail_and_errors(self):
        response = self.client.post(reverse('accounts:register'), {
            'email': 'jane@example.com',
            'password': 'S3curePass!23',
            'password_confirm': 'Different!23',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertIn('errors', response.data)

    def test_auth_required_error_keeps_single_detail_key(self):
        response = self.client.post(reverse('accounts:sessions-revoke', args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
        self.assertNotIn('errors', response.data)
