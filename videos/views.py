from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsContentManager
from core.media_access import serve_protected_media
from core.storage import safe_media_name
from videos.models import Subtitle, Video
from videos.permissions import CanAccessVideo, CanManageSubtitle
from videos.serializers import SubtitleUploadSerializer, VideoSerializer, VideoUploadSerializer
from videos.tasks import process_video
from videos.tokens import verify_hls_token


class VideoUploadView(generics.CreateAPIView):
    """Upload d'une vidéo source ; déclenche le transcodage HLS en tâche de fond."""

    serializer_class = VideoUploadSerializer
    permission_classes = [IsContentManager]

    def perform_create(self, serializer):
        video = serializer.save(owner=self.request.user)
        process_video.delay(str(video.id))


class VideoListView(generics.ListAPIView):
    """Liste ses propres vidéos (tous statuts) + les vidéos publiques disponibles des autres."""

    serializer_class = VideoSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Video.objects.select_related('owner')
        if not user.is_admin:
            queryset = queryset.filter(
                Q(owner=user) | Q(status=Video.Status.READY, visibility=Video.Visibility.PUBLIC),
            )
        movie_id = self.request.query_params.get('movie')
        if movie_id:
            queryset = queryset.filter(movie_id=movie_id)
        return queryset


class VideoDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    lookup_field = 'id'
    permission_classes = [IsAuthenticated, CanAccessVideo]


class VideoRetryView(APIView):
    """Relance le traitement d'une vidéo en échec ou bloquée."""

    permission_classes = [IsContentManager]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, id):
        video = get_object_or_404(Video, id=id)
        if video.owner != request.user and not request.user.is_admin:
            raise PermissionDenied('Vous ne pouvez relancer que vos propres vidéos.')

        video.status = Video.Status.PENDING
        video.error_message = ''
        video.save(update_fields=['status', 'error_message'])
        process_video.delay(str(video.id))
        return Response({'detail': 'Traitement relancé.'}, status=status.HTTP_202_ACCEPTED)


class SubtitleUploadView(generics.CreateAPIView):
    """Ajoute une piste de sous-titres (FR ou EN) à une vidéo dont on est propriétaire."""

    serializer_class = SubtitleUploadSerializer
    permission_classes = [IsContentManager]

    def _video(self):
        video = get_object_or_404(Video, id=self.kwargs['id'])
        if video.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied('Vous ne pouvez ajouter des sous-titres qu\'à vos propres vidéos.')
        return video

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'video': self._video()}

    def perform_create(self, serializer):
        serializer.save(video=self._video())


class SubtitleDeleteView(generics.DestroyAPIView):
    queryset = Subtitle.objects.select_related('video')
    lookup_url_kwarg = 'subtitle_id'
    lookup_field = 'id'
    permission_classes = [IsAuthenticated, CanManageSubtitle]


class ProtectedSubtitleFileView(View):
    """Sert le fichier .vtt d'une piste de sous-titres, protégé par le même token que le HLS."""

    def get(self, request, video_id, language):
        token = request.GET.get('token', '')
        if not verify_hls_token(token, video_id):
            raise Http404
        subtitle = get_object_or_404(Subtitle, video_id=video_id, language=language)
        return serve_protected_media(subtitle.file.name, content_type='text/vtt')


class ProtectedHlsFileView(View):
    """Sert les fichiers HLS (manifest + segments) d'une vidéo, jamais accessibles publiquement.

    L'accès est prouvé par un token signé et temporaire (voir videos.tokens), délivré uniquement
    par VideoDetailView après vérification de CanAccessVideo. Le lecteur (navigateur/hls.js) ne
    peut pas envoyer d'en-tête Authorization sur chaque requête de segment : le token voyage donc
    dans l'URL, et est repropagé dans chaque ligne des manifests .m3u8 (la résolution d'URL relative
    du navigateur ignore la query string de l'URL de base, on doit donc la réinjecter nous-mêmes).
    """

    def get(self, request, video_id, relpath):
        token = request.GET.get('token', '')
        if not verify_hls_token(token, video_id):
            raise Http404
        video = get_object_or_404(Video, id=video_id, status=Video.Status.READY)

        name = safe_media_name(f'hls/{video.id}', relpath)

        if name.endswith('.m3u8'):
            # Les manifests sont toujours relus et réécrits ici (quel que soit le stockage) pour y
            # propager le token ; seuls les segments .ts sont délégués (nginx ou URL S3 signée).
            if not default_storage.exists(name):
                raise Http404
            with default_storage.open(name, 'rb') as fh:
                content = fh.read().decode('utf-8')
            lines = []
            for line in content.splitlines():
                if line and not line.startswith('#'):
                    sep = '&' if '?' in line else '?'
                    line = f'{line}{sep}token={token}'
                lines.append(line)
            return HttpResponse('\n'.join(lines) + '\n', content_type='application/vnd.apple.mpegurl')

        return serve_protected_media(name, content_type='video/mp2t')
