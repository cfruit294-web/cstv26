from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdmin
from community.models import Post
from live.models import LiveStream
from messaging.models import Message
from videos.models import Video


class DashboardOverviewView(APIView):
    """Statistiques agrégées de la plateforme (utilisateurs, contenu). Réservé aux admins."""

    permission_classes = [IsAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        data = {
            'users': {
                'total': User.objects.count(),
                'new_last_30_days': User.objects.filter(date_joined__gte=last_30_days).count(),
                'by_role': {
                    row['role']: row['count']
                    for row in User.objects.values('role').annotate(count=Count('id'))
                },
            },
            'videos': {
                'total': Video.objects.count(),
                'ready': Video.objects.filter(status=Video.Status.READY).count(),
                'processing': Video.objects.filter(status=Video.Status.PROCESSING).count(),
            },
            'live': {
                'total': LiveStream.objects.count(),
                'currently_live': LiveStream.objects.filter(status=LiveStream.Status.LIVE).count(),
            },
            'community': {
                'posts': Post.objects.count(),
            },
            'messaging': {
                'messages': Message.objects.count(),
            },
        }
        return Response(data)
