from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Endpoint de supervision utilisé par Docker/Nginx/monitoring."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({'status': 'ok', 'timestamp': timezone.now()})
