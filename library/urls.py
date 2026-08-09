from django.urls import path

from library import views

app_name = 'library'

urlpatterns = [
    path('watchlist/', views.WatchlistListView.as_view(), name='watchlist-list'),
    path('watchlist/toggle/', views.WatchlistToggleView.as_view(), name='watchlist-toggle'),
    path('watchlist/status/<uuid:movie_id>/', views.WatchlistStatusView.as_view(), name='watchlist-status'),
    path('history/', views.WatchHistoryUpdateView.as_view(), name='history-update'),
    path('history/<uuid:video_id>/', views.WatchHistoryDetailView.as_view(), name='history-detail'),
]
