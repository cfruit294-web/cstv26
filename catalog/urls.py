from django.urls import path

from catalog import views

app_name = 'catalog'

urlpatterns = [
    path('omdb/search/', views.OmdbSearchView.as_view(), name='omdb-search'),
    path('movies/import/', views.MovieImportView.as_view(), name='movie-import'),
    path('movies/', views.MovieListView.as_view(), name='movie-list'),
    path('movies/<uuid:id>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('movies/<uuid:id>/recommendations/', views.MovieRecommendationsView.as_view(), name='movie-recommendations'),
]
