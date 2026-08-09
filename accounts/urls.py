from django.urls import path

from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('verify-email/resend/', views.ResendVerificationView.as_view(), name='resend-verification'),

    path('login/', views.LoginView.as_view(), name='login'),
    path('login/2fa/', views.TwoFactorLoginView.as_view(), name='login-2fa'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', views.CustomTokenRefreshView.as_view(), name='token-refresh'),

    path('me/', views.MeView.as_view(), name='me'),
    path('search/', views.UserSearchView.as_view(), name='search'),
    path('password/change/', views.ChangePasswordView.as_view(), name='password-change'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    path('2fa/enable/', views.TwoFactorEnableView.as_view(), name='2fa-enable'),
    path('2fa/enable/confirm/', views.TwoFactorEnableConfirmView.as_view(), name='2fa-enable-confirm'),
    path('2fa/disable/', views.TwoFactorDisableView.as_view(), name='2fa-disable'),

    path('sessions/', views.UserSessionListView.as_view(), name='sessions'),
    path('sessions/<int:pk>/revoke/', views.UserSessionRevokeView.as_view(), name='sessions-revoke'),
]
