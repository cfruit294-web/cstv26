from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsContentManager
from live.models import LiveChatMessage, LiveStream
from live.permissions import CanAccessLiveStream
from live.serializers import (
    LiveChatMessageSerializer,
    LiveStreamCreateSerializer,
    LiveStreamOwnerSerializer,
    LiveStreamSerializer,
)
from live.tasks import create_replay_from_stream


def _is_owner_or_admin(user, stream):
    return user.is_authenticated and (stream.owner_id == user.id or user.is_admin)


class LiveStreamCreateView(generics.CreateAPIView):
    """Planifie un nouveau live (génère automatiquement la clé de stream)."""

    serializer_class = LiveStreamCreateSerializer
    permission_classes = [IsContentManager]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LiveStreamListView(generics.ListAPIView):
    """Publique : les visiteurs anonymes voient les lives publics (page d'accueil, grille de programmation)."""

    serializer_class = LiveStreamSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        queryset = LiveStream.objects.exclude(status=LiveStream.Status.CANCELED)
        if not user.is_authenticated:
            return queryset.filter(visibility=LiveStream.Visibility.PUBLIC)
        if user.is_admin:
            return queryset
        return queryset.filter(Q(owner=user) | Q(visibility=LiveStream.Visibility.PUBLIC))


class LiveStreamDetailView(generics.RetrieveAPIView):
    """Publique : CanAccessLiveStream filtre déjà les lives privés/premium pour les non-propriétaires."""

    queryset = LiveStream.objects.all()
    lookup_field = 'id'
    permission_classes = [AllowAny, CanAccessLiveStream]

    def get_serializer_class(self):
        instance = getattr(self, '_object', None)
        if instance and _is_owner_or_admin(self.request.user, instance):
            return LiveStreamOwnerSerializer
        return LiveStreamSerializer

    def get_object(self):
        instance = super().get_object()
        self._object = instance
        return instance


class LiveStreamStartView(APIView):
    @extend_schema(request=None, responses=LiveStreamOwnerSerializer)
    def post(self, request, id):
        stream = get_object_or_404(LiveStream, id=id)
        if not _is_owner_or_admin(request.user, stream):
            raise PermissionDenied('Vous ne pouvez démarrer que vos propres lives.')

        stream.status = LiveStream.Status.LIVE
        stream.started_at = timezone.now()
        stream.save(update_fields=['status', 'started_at'])
        return Response(LiveStreamOwnerSerializer(stream).data)


class LiveStreamEndView(APIView):
    @extend_schema(request=None, responses=LiveStreamOwnerSerializer)
    def post(self, request, id):
        stream = get_object_or_404(LiveStream, id=id)
        if not _is_owner_or_admin(request.user, stream):
            raise PermissionDenied('Vous ne pouvez terminer que vos propres lives.')

        stream.status = LiveStream.Status.ENDED
        stream.ended_at = timezone.now()
        stream.save(update_fields=['status', 'ended_at'])
        return Response(LiveStreamOwnerSerializer(stream).data)


class RtmpWebhookView(APIView):
    """Callback appelé par le serveur média RTMP externe (nginx-rtmp `on_publish`/`on_publish_done`)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        secret = request.data.get('secret') or request.query_params.get('secret')
        if secret != settings.RTMP_WEBHOOK_SECRET:
            return Response(status=status.HTTP_403_FORBIDDEN)

        stream_key = request.data.get('name') or request.data.get('stream_key') or ''
        stream_key = stream_key.rsplit('/', 1)[-1]  # tolère un préfixe d'app RTMP (ex: "live/<clé>")
        try:
            stream = LiveStream.objects.get(stream_key=stream_key)
        except LiveStream.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        event = request.data.get('event', 'publish')
        if event == 'publish_done':
            stream.status = LiveStream.Status.ENDED
            stream.ended_at = timezone.now()
            stream.save(update_fields=['status', 'ended_at'])
            create_replay_from_stream.delay(str(stream.id))
        else:
            stream.status = LiveStream.Status.LIVE
            stream.started_at = timezone.now()
            stream.save(update_fields=['status', 'started_at'])

        return Response({'detail': 'ok'})


class LiveChatHistoryView(generics.ListAPIView):
    serializer_class = LiveChatMessageSerializer

    def get_queryset(self):
        stream = get_object_or_404(LiveStream, id=self.kwargs['id'])
        user = self.request.user
        if not (
            _is_owner_or_admin(user, stream)
            or (stream.visibility == LiveStream.Visibility.PUBLIC and stream.status != LiveStream.Status.CANCELED)
        ):
            raise PermissionDenied("Vous n'avez pas accès à ce live.")
        return LiveChatMessage.objects.filter(stream=stream).select_related('user')
