from django.urls import path

from live import views

app_name = 'live'

urlpatterns = [
    path('streams/', views.LiveStreamListView.as_view(), name='stream-list'),
    path('streams/create/', views.LiveStreamCreateView.as_view(), name='stream-create'),
    path('streams/<uuid:id>/', views.LiveStreamDetailView.as_view(), name='stream-detail'),
    path('streams/<uuid:id>/start/', views.LiveStreamStartView.as_view(), name='stream-start'),
    path('streams/<uuid:id>/end/', views.LiveStreamEndView.as_view(), name='stream-end'),
    path('streams/<uuid:id>/chat/', views.LiveChatHistoryView.as_view(), name='stream-chat'),
    path('webhook/rtmp/', views.RtmpWebhookView.as_view(), name='rtmp-webhook'),
]
