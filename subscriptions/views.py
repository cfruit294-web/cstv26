from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from subscriptions import services
from subscriptions.models import Plan, Subscription
from subscriptions.serializers import PlanSerializer, SubscribeSerializer, SubscriptionSerializer

ACTIVE_STATUSES = (Subscription.Status.PENDING, Subscription.Status.TRIALING, Subscription.Status.ACTIVE)


class PlanListView(generics.ListAPIView):
    """Catalogue public des formules actives."""

    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    queryset = Plan.objects.filter(is_active=True)


class PlanAdminListCreateView(generics.ListCreateAPIView):
    serializer_class = PlanSerializer
    permission_classes = [IsAdmin]
    queryset = Plan.objects.all()


class PlanAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PlanSerializer
    permission_classes = [IsAdmin]
    queryset = Plan.objects.all()
    lookup_field = 'id'


class SubscribeView(APIView):
    """Souscrit l'utilisateur courant à une formule (essai gratuit immédiat ou en attente de paiement)."""

    @extend_schema(request=SubscribeSerializer, responses=SubscriptionSerializer)
    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if Subscription.objects.filter(user=request.user, status__in=ACTIVE_STATUSES).exists():
            return Response(
                {'detail': 'Vous avez déjà un abonnement en cours ou en attente de paiement.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = services.start_subscription(request.user, serializer.plan)
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class MySubscriptionView(APIView):
    @extend_schema(responses=SubscriptionSerializer)
    def get(self, request):
        subscription = (
            Subscription.objects.filter(user=request.user)
            .exclude(status=Subscription.Status.CANCELED)
            .order_by('-created_at')
            .first()
        )
        if not subscription:
            return Response({'detail': "Aucun abonnement."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SubscriptionSerializer(subscription).data)


class CancelSubscriptionView(APIView):
    @extend_schema(request=None, responses=SubscriptionSerializer)
    def post(self, request):
        subscription = (
            Subscription.objects.filter(
                user=request.user,
                status__in=(Subscription.Status.ACTIVE, Subscription.Status.TRIALING),
            )
            .order_by('-created_at')
            .first()
        )
        if not subscription:
            return Response({'detail': 'Aucun abonnement actif à annuler.'}, status=status.HTTP_404_NOT_FOUND)

        services.cancel_subscription(subscription)
        return Response(SubscriptionSerializer(subscription).data)
