from django.urls import path

from ads import views

app_name = 'ads'

urlpatterns = [
    path('next/', views.NextAdView.as_view(), name='next-ad'),
]
