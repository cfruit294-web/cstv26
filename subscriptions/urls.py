from django.urls import path

from subscriptions import views

app_name = 'subscriptions'

urlpatterns = [
    path('plans/', views.PlanListView.as_view(), name='plan-list'),
    path('plans/admin/', views.PlanAdminListCreateView.as_view(), name='plan-admin-list'),
    path('plans/admin/<uuid:id>/', views.PlanAdminDetailView.as_view(), name='plan-admin-detail'),
    path('subscribe/', views.SubscribeView.as_view(), name='subscribe'),
    path('me/', views.MySubscriptionView.as_view(), name='my-subscription'),
    path('cancel/', views.CancelSubscriptionView.as_view(), name='cancel'),
]
