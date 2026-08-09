from django.urls import path

from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('overview/', views.DashboardOverviewView.as_view(), name='overview'),
]
