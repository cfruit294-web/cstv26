from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import BaseModel
from products.models import Product


class Order(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente de paiement'
        PAID = 'paid', 'Payée'
        CANCELED = 'canceled', 'Annulée'
        REFUNDED = 'refunded', 'Remboursée'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    shipping_address = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Commande {self.id} ({self.status})'


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity
