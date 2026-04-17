from rest_framework import serializers

from .models import Payment, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id", "name", "slug", "description", "duration_days",
            "price", "price_usd", "currency", "features",
            "is_active", "is_popular", "sort_order",
        )


class AdminPlanSerializer(serializers.ModelSerializer):
    subscription_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Plan
        fields = (
            "id", "name", "slug", "description", "duration_days",
            "price", "price_usd", "currency", "features",
            "is_active", "is_popular", "sort_order",
            "subscription_count", "created_at",
        )

    def validate_currency(self, value):
        return (value or "INR").upper()

    def validate_features(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Features must be a list.")

        cleaned = []
        for feature in value:
            if not isinstance(feature, str):
                raise serializers.ValidationError("Each feature must be a string.")
            text = feature.strip()
            if text:
                cleaned.append(text)
        return cleaned

    def validate(self, attrs):
        price = attrs.get("price", getattr(self.instance, "price", None))
        price_usd = attrs.get("price_usd", getattr(self.instance, "price_usd", None))

        if price is not None and price < 0:
            raise serializers.ValidationError({"price": "Price must be zero or greater."})
        if price_usd is not None and price_usd < 0:
            raise serializers.ValidationError({"price_usd": "USD price must be zero or greater."})

        return attrs


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
