from django.urls import path

from search import views

app_name = 'search'

urlpatterns = [
    path('', views.GlobalSearchView.as_view(), name='global-search'),
]
