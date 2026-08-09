"""Logique métier de l'app accounts : émission de jetons, envoi d'emails, gestion des sessions."""
from datetime import timedelta

import pyotp
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import EmailVerificationToken, PasswordResetToken, UserSession


def issue_tokens_for_user(user, request=None):
    """Génère une paire access/refresh JWT et enregistre la session/appareil associé(e)."""
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['email_verified'] = user.is_email_verified

    access = refresh.access_token
    access['sid'] = refresh['jti']

    UserSession.objects.create(
        user=user,
        refresh_token_jti=refresh['jti'],
        device=(request.data.get('device_name', '') if request and hasattr(request, 'data') else ''),
        user_agent=(request.META.get('HTTP_USER_AGENT', '')[:255] if request else ''),
        ip_address=_get_client_ip(request) if request else None,
    )

    return {'access': str(access), 'refresh': str(refresh)}


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_email_verification_token(user):
    return EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS),
    )


def send_verification_email(user, token):
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token.token}"
    send_mail(
        subject='Vérifiez votre adresse email',
        message=f"Bonjour {user.get_short_name()},\n\nConfirmez votre email en visitant : {verify_url}\n"
                f"Ce lien expire dans {settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS} heures.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def create_password_reset_token(user):
    return PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_TTL_HOURS),
    )


def send_password_reset_email(user, token):
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token.token}"
    send_mail(
        subject='Réinitialisation de votre mot de passe',
        message=f"Bonjour {user.get_short_name()},\n\nRéinitialisez votre mot de passe ici : {reset_url}\n"
                f"Ce lien expire dans {settings.PASSWORD_RESET_TOKEN_TTL_HOURS} heures. "
                f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def generate_two_factor_secret():
    return pyotp.random_base32()


def build_two_factor_uri(user, secret):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name='CSTV')


def verify_two_factor_code(secret, code):
    return pyotp.TOTP(secret).verify(code, valid_window=1)
