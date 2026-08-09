from django.conf import settings
from django.db import models

from core.models import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Product(BaseModel):
    """Produit de la boutique : numérique (livré par fichier) ou physique (livré par expédition)."""

    class ProductType(models.TextChoices):
        DIGITAL = 'digital', 'Numérique'
        PHYSICAL = 'physical', 'Physique'

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=10, choices=ProductType.choices, default=ProductType.DIGITAL)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')

    cover_image = models.ImageField(upload_to='products/covers/', blank=True, null=True)
    digital_file = models.FileField(upload_to='products/files/', blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self) -> bool:
        if self.product_type == self.ProductType.DIGITAL:
            return True
        return self.stock_quantity is not None and self.stock_quantity > 0
