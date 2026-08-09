from rest_framework import serializers

from subscriptions.models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            'id', 'name', 'slug', 'tier', 'description', 'price', 'currency',
            'billing_period', 'trial_days', 'features', 'is_active',
        )
        read_only_fields = ('id',)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id', 'plan', 'status', 'trial_end', 'current_period_start',
            'current_period_end', 'auto_renew', 'canceled_at', 'created_at',
        )
        read_only_fields = fields


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()

    def validate_plan_id(self, value):
        try:
            self.plan = Plan.objects.get(id=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Ce plan n'existe pas ou n'est plus disponible.")
        return value
