from django.urls import re_path

from watchparty.consumers import WatchPartyConsumer

websocket_urlpatterns = [
    re_path(r'^ws/watchparty/(?P<party_id>[0-9a-f-]+)/$', WatchPartyConsumer.as_asgi()),
]
