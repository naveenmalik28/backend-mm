from rest_framework import serializers

from .models import Payment, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ("id", "name", "slug", "duration_days", "price", "currency", "features", "is_active")


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "user_email",
            "amount",
            "currency",
            "payment_gateway",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway_signature",
            "status",
            "created_at",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "user_email",
            "plan",
            "status",
            "starts_at",
            "expires_at",
            "auto_renew",
            "created_at",
            "updated_at",
            "payments",
        )
