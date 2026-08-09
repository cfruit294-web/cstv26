"""Création et diffusion des notifications : persistance + push temps réel (WebSocket) + email optionnel."""
from django.conf import settings
from django.core.mail import send_mail

from notifications.models import Notification


def notify(user, title, body='', category=Notification.Category.INFO, link='', send_email=False):
    notification = Notification.objects.create(
        recipient=user, title=title, body=body, category=category, link=link,
    )
    _push_realtime(notification)
    if send_email:
        _send_email(notification)
    return notification


def _push_realtime(notification):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f'notifications_{notification.recipient_id}',
        {
            'type': 'notification.event',
            'id': str(notification.id),
            'category': notification.category,
            'title': notification.title,
            'body': notification.body,
            'link': notification.link,
            'created_at': notification.created_at.isoformat(),
        },
    )


def _send_email(notification):
    send_mail(
        subject=notification.title,
        message=notification.body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notification.recipient.email],
    )
