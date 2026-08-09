from django.contrib import admin

from products.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'product_type', 'price', 'currency', 'stock_quantity', 'is_active')
    list_filter = ('product_type', 'is_active', 'category')
    search_fields = ('name', 'seller__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
