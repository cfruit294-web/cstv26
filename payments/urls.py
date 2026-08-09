from django.urls import path

from payments import views

app_name = 'payments'

urlpatterns = [
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('cinetpay/notify/', views.CinetPayNotifyView.as_view(), name='cinetpay-notify'),
    path('', views.PaymentListView.as_view(), name='payment-list'),
    path('<uuid:id>/', views.PaymentDetailView.as_view(), name='payment-detail'),
]
