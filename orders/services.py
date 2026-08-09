"""Logique métier des commandes : création atomique, gestion de stock, confirmation de paiement."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product


class OrderError(Exception):
    """Levée lorsque la commande ne peut pas être créée (produit indisponible, stock insuffisant...)."""


@transaction.atomic
def create_order(user, items_payload, shipping_address=''):
    """items_payload : [{'product_id': ..., 'quantity': ...}, ...]"""
    if not items_payload:
        raise OrderError('La commande doit contenir au moins un article.')

    order = Order.objects.create(user=user, shipping_address=shipping_address)
    total = Decimal('0')
    currency = 'XOF'

    for index, item in enumerate(items_payload):
        try:
            product = Product.objects.select_for_update().get(id=item['product_id'], is_active=True)
        except Product.DoesNotExist:
            raise OrderError(f"Produit introuvable ou indisponible : {item.get('product_id')}")

        quantity = item.get('quantity', 1)
        if quantity < 1:
            raise OrderError('La quantité doit être supérieure à zéro.')

        if product.product_type == Product.ProductType.PHYSICAL:
            if product.stock_quantity is None or product.stock_quantity < quantity:
                raise OrderError(f'Stock insuffisant pour {product.name}.')

        OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=product.price)
        total += product.price * quantity
        if index == 0:
            currency = product.currency

    order.total_amount = total
    order.currency = currency
    order.save(update_fields=['total_amount', 'currency'])
    return order


@transaction.atomic
def mark_order_paid(order):
    """Marque la commande payée et décrémente le stock des produits physiques concernés."""
    if order.status == Order.Status.PAID:
        return order

    for item in order.items.select_related('product').select_for_update():
        product = item.product
        if product.product_type == Product.ProductType.PHYSICAL and product.stock_quantity is not None:
            product.stock_quantity = max(product.stock_quantity - item.quantity, 0)
            product.save(update_fields=['stock_quantity'])

    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])

    from notifications.models import Notification
    from notifications.services import notify

    notify(
        order.user,
        title='Votre commande a été payée',
        body=f'Commande {order.id} confirmée, montant {order.total_amount} {order.currency}.',
        category=Notification.Category.ORDER,
        link=f'/orders/{order.id}',
    )

    return order
