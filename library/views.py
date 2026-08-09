from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Movie
from library.models import WatchHistory, WatchlistItem
from library.serializers import WatchHistorySerializer, WatchlistItemSerializer
from videos.models import Video


class WatchlistListView(generics.ListAPIView):
    """Films que l'utilisateur courant a ajoutés à « Ma liste »."""

    serializer_class = WatchlistItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user).select_related('movie')


class WatchlistToggleView(APIView):
    """Ajoute le film à la liste s'il n'y est pas encore, le retire sinon."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        movie_id = request.data.get('movie_id')
        movie = get_object_or_404(Movie, id=movie_id)

        item, created = WatchlistItem.objects.get_or_create(user=request.user, movie=movie)
        if not created:
            item.delete()
        return Response({'in_watchlist': created})


class WatchlistStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, movie_id):
        in_watchlist = WatchlistItem.objects.filter(user=request.user, movie_id=movie_id).exists()
        return Response({'in_watchlist': in_watchlist})


class WatchHistoryUpdateView(APIView):
    """Enregistre (ou met à jour) la position de lecture courante de l'utilisateur sur une vidéo."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=WatchHistorySerializer, responses=WatchHistorySerializer)
    def post(self, request):
        video = get_object_or_404(Video, id=request.data.get('video'))
        position_seconds = request.data.get('position_seconds', 0)

        entry, _created = WatchHistory.objects.update_or_create(
            user=request.user, video=video, defaults={'position_seconds': position_seconds},
        )
        return Response(WatchHistorySerializer(entry).data, status=status.HTTP_200_OK)


class WatchHistoryDetailView(APIView):
    """Position de reprise sauvegardée pour une vidéo (0 si l'utilisateur ne l'a jamais regardée)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, video_id):
        entry = WatchHistory.objects.filter(user=request.user, video_id=video_id).first()
        return Response({'position_seconds': entry.position_seconds if entry else 0})
