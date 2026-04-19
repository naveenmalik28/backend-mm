import hashlib
import hmac
import json
import logging
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Payment, Plan, Subscription


logger = logging.getLogger(__name__)

PLAN_LIST_CACHE_KEY = "subscriptions:plan-list:v1"
SUPPORTED_CHECKOUT_CURRENCIES = {"INR", "USD"}


def invalidate_plan_cache():
    cache.delete(PLAN_LIST_CACHE_KEY)


def resolve_plan_amount(plan, requested_currency):
    currency = (requested_currency or "INR").upper()
    if currency not in SUPPORTED_CHECKOUT_CURRENCIES:
        raise ValidationError({"currency": "Unsupported currency. Use INR or USD."})

    if currency == "USD":
        if plan.price_usd <= 0:
            raise ValidationError({"currency": "USD pricing is not configured for this plan."})
        return plan.price_usd, "USD"

    return plan.price, "INR"


def get_active_plans():
    return Plan.objects.filter(is_active=True).only(
        "id",
        "name",
        "slug",
        "description",
        "duration_days",
        "price",
        "price_usd",
        "currency",
        "features",
        "is_popular",
        "sort_order",
    )


def expire_due_subscriptions(*, batch_size=1000):
    now = timezone.now()
    expired_count = 0

    while True:
        subscription_ids = list(
            Subscription.objects.filter(
                status=Subscription.STATUS_ACTIVE,
                expires_at__lte=now,
            )
            .order_by("expires_at")
            .values_list("id", flat=True)[:batch_size]
        )
        if not subscription_ids:
            return expired_count

        expired_count += Subscription.objects.filter(id__in=subscription_ids).update(
            status=Subscription.STATUS_EXPIRED,
            updated_at=now,
        )


def expire_user_subscriptions(user):
    now = timezone.now()
    return Subscription.objects.filter(
        user=user,
        status=Subscription.STATUS_ACTIVE,
        expires_at__lte=now,
    ).update(status=Subscription.STATUS_EXPIRED, updated_at=now)


def create_checkout_session(*, user, plan, requested_currency):
    import razorpay

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValidationError({"detail": "Razorpay is not configured."})

    subscription_id = uuid.uuid4()
    amount, order_currency = resolve_plan_amount(plan, requested_currency)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order = client.order.create(
        {
            "amount": int(amount * 100),
            "currency": order_currency,
            "receipt": str(subscription_id),
        }
    )

    with transaction.atomic():
        subscription = Subscription.objects.create(
            id=subscription_id,
            user=user,
            plan=plan,
            status=Subscription.STATUS_PENDING,
        )
        Payment.objects.create(
            subscription=subscription,
            user=user,
            amount=amount,
            currency=order_currency,
            payment_gateway="razorpay",
            gateway_order_id=order["id"],
            status=Payment.STATUS_PENDING,
        )

    return subscription, order


def verify_checkout_signature(*, order_id, payment_id, signature):
    if not settings.RAZORPAY_KEY_SECRET:
        raise ValidationError({"detail": "Razorpay secret is not configured."})

    generated_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature)


def activate_subscription(subscription, *, at=None):
    now = at or timezone.now()

    with transaction.atomic():
        locked_subscription = (
            Subscription.objects.select_for_update()
            .select_related("plan", "user")
            .get(pk=subscription.pk)
        )

        if (
            locked_subscription.status == Subscription.STATUS_ACTIVE
            and locked_subscription.expires_at
            and locked_subscription.expires_at > now
        ):
            return locked_subscription

        Subscription.objects.select_for_update().filter(
            user=locked_subscription.user,
            status=Subscription.STATUS_ACTIVE,
            expires_at__lte=now,
        ).exclude(pk=locked_subscription.pk).update(
            status=Subscription.STATUS_EXPIRED,
            updated_at=now,
        )

        Subscription.objects.select_for_update().filter(
            user=locked_subscription.user,
            status=Subscription.STATUS_ACTIVE,
        ).exclude(pk=locked_subscription.pk).update(
            status=Subscription.STATUS_CANCELLED,
            updated_at=now,
        )

        locked_subscription.activate(at=now)
        return locked_subscription


def process_successful_payment(*, user, subscription_id, order_id, payment_id, signature, requested_currency=None):
    if not verify_checkout_signature(order_id=order_id, payment_id=payment_id, signature=signature):
        raise ValidationError({"razorpay_signature": "Invalid signature."})

    now = timezone.now()
    with transaction.atomic():
        try:
            payment = (
                Payment.objects.select_for_update()
                .select_related("subscription__plan")
                .get(
                    subscription_id=subscription_id,
                    user=user,
                    payment_gateway="razorpay",
                    gateway_order_id=order_id,
                )
            )
        except Payment.DoesNotExist as exc:
            raise ValidationError({"subscription_id": "Pending payment session was not found."}) from exc

        subscription = payment.subscription
        if subscription.user_id != user.id:
            raise ValidationError({"subscription_id": "Subscription does not belong to the authenticated user."})

        if payment.status == Payment.STATUS_SUCCESS:
            return payment, subscription, False

        if payment.gateway_payment_id and payment.gateway_payment_id != payment_id:
            raise ValidationError({"razorpay_payment_id": "Payment was already processed with a different gateway id."})

        amount, currency = resolve_plan_amount(subscription.plan, requested_currency or payment.currency)
        payment.amount = amount
        payment.currency = currency
        payment.gateway_payment_id = payment_id
        payment.gateway_signature = signature
        payment.status = Payment.STATUS_SUCCESS
        payment.save(
            update_fields=[
                "amount",
                "currency",
                "gateway_payment_id",
                "gateway_signature",
                "status",
            ]
        )

        subscription = activate_subscription(subscription, at=now)

    return payment, subscription, True


def verify_webhook_signature(*, raw_body, signature):
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise ValidationError({"detail": "Webhook secret is not configured."})

    generated_signature = hmac.new(
        webhook_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(generated_signature, signature or ""):
        raise ValidationError({"detail": "Invalid webhook signature."})


def process_razorpay_webhook(*, raw_body, signature):
    verify_webhook_signature(raw_body=raw_body, signature=signature)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError({"detail": "Invalid webhook payload."}) from exc

    event = payload.get("event")
    if event != "payment.captured":
        return event, False

    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )
    order_id = payment_entity.get("order_id") or payment_entity.get("order", {}).get("id")
    payment_id = payment_entity.get("id")
    if not order_id or not payment_id:
        raise ValidationError({"detail": "Webhook payload is missing order or payment identifiers."})

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("subscription__plan", "user")
            .filter(payment_gateway="razorpay", gateway_order_id=order_id)
            .first()
        )
        if not payment:
            logger.warning("Received Razorpay webhook for unknown order_id=%s", order_id)
            return event, False

        changed = False
        if not payment.gateway_payment_id:
            payment.gateway_payment_id = payment_id
            changed = True

        if payment.status != Payment.STATUS_SUCCESS:
            payment.status = Payment.STATUS_SUCCESS
            changed = True

        if changed:
            payment.save(update_fields=["gateway_payment_id", "status"])

    if changed or payment.subscription.status != Subscription.STATUS_ACTIVE:
        activate_subscription(payment.subscription)
    return event, True
