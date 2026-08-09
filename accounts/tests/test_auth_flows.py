import pyotp
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import EmailVerificationToken, PasswordResetToken, User


class RegistrationAndEmailVerificationTests(APITestCase):
    def test_register_creates_inactive_email_and_sends_token(self):
        url = reverse('accounts:register')
        payload = {
            'email': 'jane@example.com',
            'full_name': 'Jane Doe',
            'password': 'S3curePass!23',
            'password_confirm': 'S3curePass!23',
        }
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email='jane@example.com')
        self.assertFalse(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())

    def test_register_rejects_mismatched_passwords(self):
        url = reverse('accounts:register')
        payload = {
            'email': 'jane@example.com',
            'password': 'S3curePass!23',
            'password_confirm': 'Different!23',
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_activates_account(self):
        user = User.objects.create_user(email='jane@example.com', password='S3curePass!23')
        from accounts import services
        token = services.create_email_verification_token(user)

        response = self.client.post(reverse('accounts:verify-email'), {'token': str(token.token)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_verify_email_rejects_reused_token(self):
        user = User.objects.create_user(email='jane@example.com', password='S3curePass!23')
        from accounts import services
        token = services.create_email_verification_token(user)
        token.mark_used()

        response = self.client.post(reverse('accounts:verify-email'), {'token': str(token.token)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAndTokenTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='jane@example.com', password='S3curePass!23')

    def test_login_returns_jwt_pair(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_rejects_wrong_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'wrong-password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_endpoint_requires_authentication(self):
        response = self.client.get(reverse('accounts:me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_returns_current_user(self):
        login = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        access = login.data['access']

        response = self.client.get(reverse('accounts:me'), HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'jane@example.com')

    def test_refresh_rotates_token_and_old_one_is_blacklisted(self):
        login = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        old_refresh = login.data['refresh']

        refresh_response = self.client.post(reverse('accounts:token-refresh'), {'refresh': old_refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

        reuse_response = self.client.post(reverse('accounts:token-refresh'), {'refresh': old_refresh})
        self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        access, refresh = login.data['access'], login.data['refresh']

        logout_response = self.client.post(
            reverse('accounts:logout'), {'refresh': refresh}, HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        reuse_response = self.client.post(reverse('accounts:token-refresh'), {'refresh': refresh})
        self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='jane@example.com', password='OldPass!234')

    def test_password_reset_flow(self):
        request_response = self.client.post(reverse('accounts:password-reset'), {'email': 'jane@example.com'})
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        token = PasswordResetToken.objects.get(user=self.user)

        confirm_response = self.client.post(reverse('accounts:password-reset-confirm'), {
            'token': str(token.token), 'new_password': 'NewPass!456',
        })
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        login_response = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'NewPass!456',
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_password_reset_request_is_silent_for_unknown_email(self):
        response = self.client.post(reverse('accounts:password-reset'), {'email': 'ghost@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PasswordResetToken.objects.exists())


class TwoFactorAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='jane@example.com', password='S3curePass!23')
        login = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        self.access = login.data['access']

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self.access}'}

    def test_enable_and_login_with_2fa(self):
        enable_response = self.client.post(reverse('accounts:2fa-enable'), **self._auth())
        self.assertEqual(enable_response.status_code, status.HTTP_200_OK)
        secret = enable_response.data['secret']

        code = pyotp.TOTP(secret).now()
        confirm_response = self.client.post(
            reverse('accounts:2fa-enable-confirm'), {'code': code}, **self._auth(),
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)

        login_response = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        self.assertTrue(login_response.data['two_factor_required'])
        pre_auth_token = login_response.data['pre_auth_token']

        second_factor_response = self.client.post(reverse('accounts:login-2fa'), {
            'pre_auth_token': pre_auth_token, 'code': pyotp.TOTP(secret).now(),
        })
        self.assertEqual(second_factor_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', second_factor_response.data)

    def test_login_2fa_rejects_wrong_code(self):
        enable_response = self.client.post(reverse('accounts:2fa-enable'), **self._auth())
        secret = enable_response.data['secret']
        self.client.post(reverse('accounts:2fa-enable-confirm'), {'code': pyotp.TOTP(secret).now()}, **self._auth())

        login_response = self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23',
        })
        pre_auth_token = login_response.data['pre_auth_token']

        response = self.client.post(reverse('accounts:login-2fa'), {
            'pre_auth_token': pre_auth_token, 'code': '000000',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserSessionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='jane@example.com', password='S3curePass!23')

    def _login(self, device_name):
        return self.client.post(reverse('accounts:login'), {
            'email': 'jane@example.com', 'password': 'S3curePass!23', 'device_name': device_name,
        })

    def test_sessions_list_and_revoke(self):
        login_a = self._login('Chrome - Windows')
        login_b = self._login('Safari - iPhone')
        access_a = login_a.data['access']

        sessions_response = self.client.get(reverse('accounts:sessions'), HTTP_AUTHORIZATION=f'Bearer {access_a}')
        self.assertEqual(sessions_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(sessions_response.data['results']), 2)

        session_b_id = next(
            s['id'] for s in sessions_response.data['results'] if s['device'] == 'Safari - iPhone'
        )
        revoke_response = self.client.post(
            reverse('accounts:sessions-revoke', args=[session_b_id]), HTTP_AUTHORIZATION=f'Bearer {access_a}',
        )
        self.assertEqual(revoke_response.status_code, status.HTTP_200_OK)

        reuse_response = self.client.post(reverse('accounts:token-refresh'), {'refresh': login_b.data['refresh']})
        self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)


class RolePermissionTests(APITestCase):
    def test_role_defaults_to_user_and_is_admin_false(self):
        user = User.objects.create_user(email='jane@example.com', password='S3curePass!23')
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_admin)

    def test_superuser_is_always_admin(self):
        admin = User.objects.create_superuser(email='admin@example.com', password='S3curePass!23')
        self.assertTrue(admin.is_admin)
        self.assertEqual(admin.role, User.Role.ADMIN)
