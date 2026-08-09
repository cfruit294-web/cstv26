from django.contrib import admin

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'amount', 'currency', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider')
    search_fields = ('transaction_id', 'user__email')
    readonly_fields = ('id', 'raw_response', 'created_at', 'updated_at')
