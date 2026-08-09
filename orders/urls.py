from django.urls import path

from orders import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order-list'),
    path('create/', views.OrderCreateView.as_view(), name='order-create'),
    path('<uuid:id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:id>/checkout/', views.OrderCheckoutView.as_view(), name='order-checkout'),
    path('<uuid:id>/download/<uuid:product_id>/', views.OrderDigitalDownloadView.as_view(), name='order-download'),
]
