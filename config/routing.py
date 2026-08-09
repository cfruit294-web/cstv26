from live.routing import websocket_urlpatterns as live_websocket_urlpatterns
from messaging.routing import websocket_urlpatterns as messaging_websocket_urlpatterns
from notifications.routing import websocket_urlpatterns as notifications_websocket_urlpatterns
from watchparty.routing import websocket_urlpatterns as watchparty_websocket_urlpatterns

websocket_urlpatterns = (
    live_websocket_urlpatterns
    + messaging_websocket_urlpatterns
    + notifications_websocket_urlpatterns
    + watchparty_websocket_urlpatterns
)
