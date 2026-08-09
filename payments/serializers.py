from rest_framework import serializers

from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id', 'provider', 'transaction_id', 'amount', 'currency', 'status',
            'payment_url', 'description', 'created_at', 'updated_at',
        )
        read_only_fields = fields
