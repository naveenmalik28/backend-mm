from rest_framework import serializers
from django.utils import timezone

from .models import Payment, Plan, Subscription
from .services import SUPPORTED_CHECKOUT_CURRENCIES


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id", "name", "slug", "description", "duration_days",
            "price", "price_usd", "currency", "features",
            "is_popular", "sort_order",
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
    class Meta:
        model = Payment
        fields = (
            "id",
            "amount",
            "currency",
            "payment_gateway",
            "status",
            "created_at",
        )


class AdminPaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "user_email",
            "amount",
            "currency",
            "payment_gateway",
            "status",
            "created_at",
        )


class CheckoutSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(min_value=1)
    currency = serializers.ChoiceField(choices=tuple(sorted(SUPPORTED_CHECKOUT_CURRENCIES)), required=False)


class PaymentVerifySerializer(serializers.Serializer):
    subscription_id = serializers.UUIDField()
    razorpay_order_id = serializers.CharField(max_length=200)
    razorpay_payment_id = serializers.CharField(max_length=200)
    razorpay_signature = serializers.CharField(max_length=500)
    currency = serializers.ChoiceField(choices=tuple(sorted(SUPPORTED_CHECKOUT_CURRENCIES)), required=False)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    latest_payment = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

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
            "is_active",
            "created_at",
            "updated_at",
            "latest_payment",
        )

    def get_latest_payment(self, obj):
        payment = getattr(obj, "latest_successful_payment", None)
        if payment is None:
            prefetched_payments = getattr(obj, "_prefetched_objects_cache", {}).get("payments")
            if prefetched_payments is not None:
                payment = prefetched_payments[0] if prefetched_payments else None
            else:
                payment = obj.payments.order_by("-created_at").first()
        return PaymentSerializer(payment).data if payment else None

    def get_is_active(self, obj):
        return obj.status == Subscription.STATUS_ACTIVE and bool(obj.expires_at and obj.expires_at > timezone.now())


class AdminSubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    is_active = serializers.SerializerMethodField()

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
            "is_active",
            "created_at",
            "updated_at",
        )

    def get_is_active(self, obj):
        return obj.status == Subscription.STATUS_ACTIVE and bool(obj.expires_at and obj.expires_at > timezone.now())
