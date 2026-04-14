import hashlib
import hmac

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment, Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer


class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.filter(is_active=True)
    permission_classes = [permissions.AllowAny]
    serializer_class = PlanSerializer
    pagination_class = None


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import razorpay

        plan_id = request.data.get("plan_id")
        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        subscription = Subscription.objects.create(user=request.user, plan=plan)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount": int(plan.price * 100),
            "currency": plan.currency,
            "receipt": str(subscription.id),
        })
        return Response({
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "subscription_id": str(subscription.id),
            "razorpay_key": settings.RAZORPAY_KEY_ID,
        })


class PaymentVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        subscription = get_object_or_404(Subscription, id=data.get("subscription_id"), user=request.user)
        message = f"{data.get('razorpay_order_id')}|{data.get('razorpay_payment_id')}".encode()
        generated_sig = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()
        if generated_sig != data.get("razorpay_signature"):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        Payment.objects.create(
            subscription=subscription,
            user=request.user,
            amount=subscription.plan.price,
            currency=subscription.plan.currency,
            payment_gateway="razorpay",
            gateway_order_id=data.get("razorpay_order_id", ""),
            gateway_payment_id=data.get("razorpay_payment_id", ""),
            gateway_signature=data.get("razorpay_signature", ""),
            status=Payment.STATUS_SUCCESS,
        )
        subscription.activate()
        return Response({"status": "subscription activated"})


class CurrentSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = request.user.subscriptions.select_related("plan").prefetch_related("payments").first()
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


# Create your views here.
