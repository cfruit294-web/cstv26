from django.contrib.auth import authenticate, password_validation
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import User, UserSession


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'phone_number', 'avatar', 'role',
            'is_email_verified', 'two_factor_enabled', 'date_joined',
        )
        read_only_fields = ('id', 'email', 'role', 'is_email_verified', 'two_factor_enabled', 'date_joined')


class UserSearchResultSerializer(serializers.ModelSerializer):
    """Résultat de recherche minimal (ex: pour démarrer une conversation) : aucune donnée sensible."""

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'avatar')
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'full_name', 'password', 'password_confirm')

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Un compte existe déjà avec cet email.'))
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': _('Les mots de passe ne correspondent pas.')})
        password_validation.validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    device_name = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        user = authenticate(
            self.context['request'],
            email=attrs['email'].lower().strip(),
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError(_('Email ou mot de passe incorrect.'))
        if not user.is_active:
            raise serializers.ValidationError(_('Ce compte est désactivé.'))
        attrs['user'] = user
        return attrs


class TwoFactorLoginSerializer(serializers.Serializer):
    pre_auth_token = serializers.CharField()
    code = serializers.CharField(min_length=6, max_length=6)
    device_name = serializers.CharField(required=False, allow_blank=True, default='')


class TwoFactorEnableConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)


class TwoFactorDisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        password_validation.validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError(_('Mot de passe actuel incorrect.'))
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value)
        return value


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = ('id', 'device', 'user_agent', 'ip_address', 'created_at', 'last_used_at', 'is_current')

    def get_is_current(self, obj) -> bool:
        current_jti = self.context.get('current_jti')
        return bool(current_jti) and obj.refresh_token_jti == current_jti
