from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ads.models import Ad
from ads.serializers import AdSerializer


class NextAdView(APIView):
    """Renvoie une publicité active au hasard pour l'emplacement demandé (aucune si aucune n'est active)."""

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('placement', OpenApiTypes.STR, required=False, default=Ad.Placement.PRE_ROLL),
        ],
        responses=AdSerializer,
    )
    def get(self, request):
        placement = request.query_params.get('placement', Ad.Placement.PRE_ROLL)
        ad = Ad.objects.filter(placement=placement, is_active=True).order_by('?').first()
        if not ad:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(AdSerializer(ad, context={'request': request}).data)
