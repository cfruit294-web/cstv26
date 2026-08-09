from django.conf import settings
from django.core import signing
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from accounts import services
from accounts.models import EmailVerificationToken, PasswordResetToken, User, UserSession
from accounts.serializers import (
    ChangePasswordSerializer,
    EmailVerificationConfirmSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    TwoFactorDisableSerializer,
    TwoFactorEnableConfirmSerializer,
    TwoFactorLoginSerializer,
    UserSearchResultSerializer,
    UserSerializer,
    UserSessionSerializer,
)

TWO_FACTOR_SALT = 'accounts.two_factor_preauth'


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = services.create_email_verification_token(user)
        services.send_verification_email(user, token)

        return Response(
            {
                'detail': "Compte créé. Vérifiez votre boîte email pour activer votre compte.",
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=EmailVerificationConfirmSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = get_object_or_404(EmailVerificationToken, token=serializer.validated_data['token'])
        if not token.is_valid():
            return Response(
                {'detail': 'Ce lien de vérification est invalide ou a expiré.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token.mark_used()
        user = token.user
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        return Response({'detail': 'Email vérifié avec succès.'})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=ResendVerificationSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        generic_response = Response({'detail': 'Si ce compte existe, un email a été envoyé.'})
        try:
            user = User.objects.get(email=serializer.validated_data['email'].lower().strip())
        except User.DoesNotExist:
            return generic_response

        if not user.is_email_verified:
            token = services.create_email_verification_token(user)
            services.send_verification_email(user, token)
        return generic_response


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user.two_factor_enabled:
            pre_auth_token = signing.dumps({'user_id': str(user.id)}, salt=TWO_FACTOR_SALT)
            return Response({'two_factor_required': True, 'pre_auth_token': pre_auth_token})

        tokens = services.issue_tokens_for_user(user, request)
        return Response({'user': UserSerializer(user).data, **tokens})


class TwoFactorLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=TwoFactorLoginSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = TwoFactorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = signing.loads(
                serializer.validated_data['pre_auth_token'],
                salt=TWO_FACTOR_SALT,
                max_age=settings.TWO_FACTOR_PREAUTH_TTL_SECONDS,
            )
        except signing.BadSignature:
            return Response(
                {'detail': 'Jeton de pré-authentification invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(User, id=payload['user_id'])
        if not services.verify_two_factor_code(user.two_factor_secret, serializer.validated_data['code']):
            return Response({'detail': 'Code de vérification incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        tokens = services.issue_tokens_for_user(user, request)
        return Response({'user': UserSerializer(user).data, **tokens})


class CustomTokenRefreshView(TokenRefreshView):
    """Synchronise UserSession avec le nouveau jti lors de la rotation du refresh token."""

    def post(self, request, *args, **kwargs):
        raw_refresh = request.data.get('refresh')
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200 and raw_refresh:
            try:
                old_jti = RefreshToken(raw_refresh)['jti']
                new_refresh = response.data.get('refresh')
                if new_refresh:
                    new_jti = RefreshToken(new_refresh)['jti']
                    UserSession.objects.filter(refresh_token_jti=old_jti).update(refresh_token_jti=new_jti)
            except TokenError:
                pass

        return response


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            jti = token['jti']
            token.blacklist()
        except TokenError:
            return Response({'detail': 'Jeton de rafraîchissement invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        UserSession.objects.filter(user=request.user, refresh_token_jti=jti).update(revoked_at=timezone.now())
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserSearchView(generics.ListAPIView):
    """Recherche minimale par email/nom (ex: démarrer une conversation) : jamais anonyme, jamais tout l'annuaire."""

    serializer_class = UserSearchResultSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query:
            return User.objects.none()
        return (
            User.objects.filter(Q(email__icontains=query) | Q(full_name__icontains=query))
            .exclude(id=self.request.user.id)
            .order_by('email')[:20]
        )


class ChangePasswordView(APIView):
    @extend_schema(request=ChangePasswordSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Mot de passe modifié avec succès.'})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        generic_response = Response({'detail': 'Si ce compte existe, un email de réinitialisation a été envoyé.'})
        try:
            user = User.objects.get(email=serializer.validated_data['email'].lower().strip())
        except User.DoesNotExist:
            return generic_response

        token = services.create_password_reset_token(user)
        services.send_password_reset_email(user, token)
        return generic_response


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = get_object_or_404(PasswordResetToken, token=serializer.validated_data['token'])
        if not token.is_valid():
            return Response({'detail': 'Ce lien est invalide ou a expiré.'}, status=status.HTTP_400_BAD_REQUEST)

        token.mark_used()
        user = token.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})


class TwoFactorEnableView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        user = request.user
        if user.two_factor_enabled:
            return Response(
                {'detail': "L'authentification à deux facteurs est déjà activée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = services.generate_two_factor_secret()
        user.two_factor_secret = secret
        user.save(update_fields=['two_factor_secret'])
        return Response({'secret': secret, 'otpauth_uri': services.build_two_factor_uri(user, secret)})


class TwoFactorEnableConfirmView(APIView):
    @extend_schema(request=TwoFactorEnableConfirmSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = TwoFactorEnableConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.two_factor_secret:
            return Response({'detail': "Initialisez d'abord la 2FA."}, status=status.HTTP_400_BAD_REQUEST)
        if not services.verify_two_factor_code(user.two_factor_secret, serializer.validated_data['code']):
            return Response({'detail': 'Code invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        user.two_factor_enabled = True
        user.save(update_fields=['two_factor_enabled'])
        return Response({'detail': 'Authentification à deux facteurs activée.'})


class TwoFactorDisableView(APIView):
    @extend_schema(request=TwoFactorDisableSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.check_password(serializer.validated_data['password']):
            return Response({'detail': 'Mot de passe incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        user.two_factor_enabled = False
        user.two_factor_secret = ''
        user.save(update_fields=['two_factor_enabled', 'two_factor_secret'])
        return Response({'detail': 'Authentification à deux facteurs désactivée.'})


class UserSessionListView(generics.ListAPIView):
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, revoked_at__isnull=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['current_jti'] = self.request.auth.get('sid') if self.request.auth else None
        return context


class UserSessionRevokeView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        session = get_object_or_404(UserSession, pk=pk, user=request.user)
        session.revoke()
        return Response({'detail': 'Session révoquée.'})
