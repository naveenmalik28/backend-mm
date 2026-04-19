from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, IntegerField, Prefetch, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment, Plan, Subscription
from .serializers import (
    CheckoutSerializer,
    PaymentVerifySerializer,
    PlanSerializer,
    SubscriptionSerializer,
)
from .services import (
    PLAN_LIST_CACHE_KEY,
    create_checkout_session,
    expire_user_subscriptions,
    get_active_plans,
    process_razorpay_webhook,
    process_successful_payment,
)
from .throttles import CheckoutThrottle, PaymentVerifyThrottle, PaymentWebhookThrottle


class PlanListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PlanSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        cached_payload = cache.get(PLAN_LIST_CACHE_KEY)
        if cached_payload is not None:
            return Response(cached_payload)

        data = self.get_serializer(get_active_plans(), many=True).data
        cache.set(PLAN_LIST_CACHE_KEY, data, timeout=getattr(settings, "SUBSCRIPTION_PLAN_CACHE_TTL", 900))
        return Response(data)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [CheckoutThrottle]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = get_object_or_404(Plan, id=serializer.validated_data["plan_id"], is_active=True)
        subscription, order = create_checkout_session(
            user=request.user,
            plan=plan,
            requested_currency=serializer.validated_data.get("currency"),
        )
        return Response(
            {
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "subscription_id": str(subscription.id),
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "plan": PlanSerializer(plan).data,
            }
        )


class PaymentVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PaymentVerifyThrottle]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _, subscription, created = process_successful_payment(
            user=request.user,
            subscription_id=serializer.validated_data["subscription_id"],
            order_id=serializer.validated_data["razorpay_order_id"],
            payment_id=serializer.validated_data["razorpay_payment_id"],
            signature=serializer.validated_data["razorpay_signature"],
            requested_currency=serializer.validated_data.get("currency"),
        )
        return Response(
            {
                "status": "subscription activated" if created else "payment already processed",
                "subscription": SubscriptionSerializer(subscription).data,
            }
        )


class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PaymentWebhookThrottle]

    def post(self, request):
        event, processed = process_razorpay_webhook(
            raw_body=request.body,
            signature=request.headers.get("X-Razorpay-Signature"),
        )
        return Response({"received": True, "event": event, "processed": processed})


class CurrentSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        expire_user_subscriptions(request.user)
        subscription = (
            Subscription.objects.select_related("plan", "user")
            .prefetch_related(
                Prefetch(
                    "payments",
                    queryset=Payment.objects.only(
                        "id",
                        "subscription_id",
                        "user_id",
                        "amount",
                        "currency",
                        "payment_gateway",
                        "status",
                        "created_at",
                    ).order_by("-created_at"),
                )
            )
            .filter(user=request.user)
            .exclude(status=Subscription.STATUS_CANCELLED)
            .order_by(
                Case(
                    When(status=Subscription.STATUS_ACTIVE, then=Value(0)),
                    When(status=Subscription.STATUS_PENDING, then=Value(1)),
                    When(status=Subscription.STATUS_EXPIRED, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                ),
                "-created_at",
            )
            .first()
        )
        if not subscription:
            return Response({"detail": "No subscription found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SubscriptionSerializer(subscription).data)


class CancelSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
        subscription.status = Subscription.STATUS_CANCELLED
        subscription.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
