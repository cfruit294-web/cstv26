from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.media_access import serve_protected_media
from orders import services
from orders.models import Order, OrderItem
from orders.serializers import OrderCreateSerializer, OrderSerializer
from orders.tokens import generate_download_token, verify_download_token
from payments import services as payment_services
from payments.models import Payment
from payments.serializers import PaymentSerializer
from products.models import Product


class OrderCreateView(APIView):
    """Crée une commande à partir d'une liste d'articles (vérifie disponibilité/stock)."""

    @extend_schema(request=OrderCreateSerializer, responses=OrderSerializer)
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = services.create_order(
                request.user,
                serializer.validated_data['items'],
                serializer.validated_data['shipping_address'],
            )
        except services.OrderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Order.objects.all()
        return Order.objects.filter(user=user)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Order.objects.all()
        return Order.objects.filter(user=user)


class OrderCheckoutView(APIView):
    """Initie le paiement CinetPay d'une commande en attente."""

    @extend_schema(request=None, responses=PaymentSerializer)
    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)
        if order.status != Order.Status.PENDING:
            return Response(
                {'detail': "Cette commande n'est pas en attente de paiement."}, status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_id = payment_services.generate_transaction_id()
        notify_url = request.build_absolute_uri(reverse('payments:cinetpay-notify'))
        return_url = f'{settings.FRONTEND_URL}/orders/return'
        description = f'Commande {order.id}'

        try:
            result = payment_services.initiate_payment(
                transaction_id=transaction_id,
                amount=order.total_amount,
                currency=order.currency,
                description=description,
                customer_email=request.user.email,
                notify_url=notify_url,
                return_url=return_url,
            )
        except payment_services.CinetPayError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        payment = Payment.objects.create(
            user=request.user,
            order=order,
            transaction_id=transaction_id,
            amount=order.total_amount,
            currency=order.currency,
            payment_url=result.get('payment_url', ''),
            description=description,
            raw_response=result,
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class OrderDigitalDownloadView(APIView):
    """Retourne l'URL de téléchargement d'un produit numérique d'une commande payée."""

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def get(self, request, id, product_id):
        order = get_object_or_404(Order, id=id, user=request.user)
        if order.status != Order.Status.PAID:
            return Response(
                {'detail': "Cette commande n'est pas encore payée."}, status=status.HTTP_403_FORBIDDEN,
            )

        item = get_object_or_404(order.items, product_id=product_id)
        product = item.product
        if product.product_type != Product.ProductType.DIGITAL or not product.digital_file:
            return Response(
                {'detail': 'Aucun fichier numérique disponible pour ce produit.'}, status=status.HTTP_404_NOT_FOUND,
            )

        token = generate_download_token(order.id, product.id)
        download_url = request.build_absolute_uri(f'{product.digital_file.url}?token={token}')
        return Response({'download_url': download_url})


class ProtectedProductFileView(View):
    """Sert un fichier numérique acheté, jamais accessible publiquement.

    L'accès est prouvé par un token signé et temporaire (voir orders.tokens), délivré uniquement
    par OrderDigitalDownloadView après vérification que la commande appartient à l'utilisateur et
    est payée. Revérifie en base que le token correspond bien à une commande payée contenant
    exactement ce fichier, pour empêcher qu'un token valide serve à récupérer un autre produit.
    """

    def get(self, request, filename):
        payload = verify_download_token(request.GET.get('token', ''))
        if not payload:
            raise Http404

        relative_path = f'products/files/{filename}'
        item = OrderItem.objects.filter(
            order_id=payload['order_id'],
            product_id=payload['product_id'],
            order__status=Order.Status.PAID,
            product__digital_file=relative_path,
        ).select_related('product').first()
        if not item:
            raise Http404

        return serve_protected_media(relative_path, download_name=filename)
