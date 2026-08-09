from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import EmailVerificationToken, PasswordResetToken, User, UserSession


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('-date_joined',)
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_email_verified', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_email_verified', 'is_staff', 'two_factor_enabled')
    search_fields = ('email', 'full_name', 'phone_number')
    readonly_fields = ('id', 'date_joined', 'updated_at', 'last_login')

    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Informations personnelles', {'fields': ('full_name', 'phone_number', 'avatar')}),
        ('Rôle et statut', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_email_verified')}),
        ('Sécurité', {'fields': ('two_factor_enabled',)}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'ip_address', 'created_at', 'last_used_at', 'revoked_at')
    list_filter = ('revoked_at',)
    search_fields = ('user__email', 'device', 'ip_address')
    readonly_fields = [f.name for f in UserSession._meta.fields]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'used_at')
    search_fields = ('user__email',)
    readonly_fields = [f.name for f in EmailVerificationToken._meta.fields]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'used_at')
    search_fields = ('user__email',)
    readonly_fields = [f.name for f in PasswordResetToken._meta.fields]
