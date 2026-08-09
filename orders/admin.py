from django.contrib import admin

from orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('id', 'product', 'quantity', 'unit_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'currency', 'paid_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('id', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
