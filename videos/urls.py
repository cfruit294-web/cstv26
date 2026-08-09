from django.urls import path

from videos import views

app_name = 'videos'

urlpatterns = [
    path('', views.VideoListView.as_view(), name='video-list'),
    path('upload/', views.VideoUploadView.as_view(), name='video-upload'),
    path('<uuid:id>/', views.VideoDetailView.as_view(), name='video-detail'),
    path('<uuid:id>/retry/', views.VideoRetryView.as_view(), name='video-retry'),
    path('<uuid:id>/subtitles/', views.SubtitleUploadView.as_view(), name='video-subtitle-upload'),
    path('subtitles/<uuid:subtitle_id>/', views.SubtitleDeleteView.as_view(), name='subtitle-delete'),
]
