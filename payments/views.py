from django.conf import settings
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from payments import services
from payments.models import Payment
from payments.serializers import PaymentSerializer
from subscriptions import services as subscription_services
from subscriptions.models import Subscription


class CheckoutView(APIView):
    """Initie le paiement CinetPay de l'abonnement en attente de l'utilisateur courant."""

    @extend_schema(request=None, responses=PaymentSerializer)
    def post(self, request):
        subscription = (
            Subscription.objects.filter(user=request.user, status=Subscription.Status.PENDING)
            .order_by('-created_at')
            .first()
        )
        if not subscription:
            return Response(
                {'detail': "Aucun abonnement en attente de paiement."}, status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_id = services.generate_transaction_id()
        notify_url = request.build_absolute_uri(reverse('payments:cinetpay-notify'))
        return_url = f'{settings.FRONTEND_URL}/payments/return'
        description = f'Abonnement {subscription.plan.name}'

        try:
            result = services.initiate_payment(
                transaction_id=transaction_id,
                amount=subscription.plan.price,
                currency=subscription.plan.currency,
                description=description,
                customer_email=request.user.email,
                notify_url=notify_url,
                return_url=return_url,
            )
        except services.CinetPayError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        payment = Payment.objects.create(
            user=request.user,
            subscription=subscription,
            transaction_id=transaction_id,
            amount=subscription.plan.price,
            currency=subscription.plan.currency,
            payment_url=result.get('payment_url', ''),
            description=description,
            raw_response=result,
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class CinetPayNotifyView(APIView):
    """Callback serveur-à-serveur CinetPay : ne fait jamais confiance au payload seul, revérifie via l'API."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        transaction_id = request.data.get('cpm_trans_id') or request.data.get('transaction_id')
        if not transaction_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            check_response = services.check_payment_status(transaction_id)
        except services.CinetPayError:
            return Response(status=status.HTTP_502_BAD_GATEWAY)

        cinetpay_status = services.extract_status(check_response)
        payment.raw_response = check_response

        if cinetpay_status == 'ACCEPTED':
            payment.status = Payment.Status.SUCCESS
            if payment.subscription:
                subscription_services.activate_subscription(payment.subscription)
        elif cinetpay_status == 'REFUSED':
            payment.status = Payment.Status.FAILED

        payment.save()
        return Response({'detail': 'ok'})


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)
