from django.urls import re_path

from live.consumers import LiveChatConsumer

websocket_urlpatterns = [
    re_path(r'^ws/live/(?P<stream_id>[0-9a-f-]+)/chat/$', LiveChatConsumer.as_asgi()),
]
