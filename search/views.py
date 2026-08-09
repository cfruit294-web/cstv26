from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.serializers import MovieSerializer
from community.serializers import PostSerializer
from live.serializers import LiveStreamSerializer
from search import services
from videos.serializers import VideoSerializer


class GlobalSearchView(APIView):
    """Recherche globale (contenu public uniquement) sur films/vidéos/lives/publications."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[OpenApiParameter('q', OpenApiTypes.STR, required=True, description='Terme recherché')],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        query = request.query_params.get('q', '')
        results = services.global_search(query)
        context = {'request': request}

        return Response({
            'query': query,
            'movies': MovieSerializer(results['movies'], many=True, context=context).data,
            'videos': VideoSerializer(results['videos'], many=True, context=context).data,
            'live_streams': LiveStreamSerializer(results['live_streams'], many=True, context=context).data,
            'posts': PostSerializer(results['posts'], many=True, context=context).data,
        })
