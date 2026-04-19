import hashlib
import hmac
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Payment, Plan, Subscription
from .serializers import PaymentSerializer
from .services import PLAN_LIST_CACHE_KEY, activate_subscription, process_successful_payment


User = get_user_model()


@override_settings(
    RAZORPAY_KEY_SECRET="test_secret",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "subscriptions-tests",
        }
    },
)
class SubscriptionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            username="user1",
            password="strong-password",
        )
        self.plan = Plan.objects.create(
            name="Starter",
            slug="starter",
            duration_days=30,
            price="999.00",
            price_usd="19.00",
            features=["A"],
            is_active=True,
        )

    def test_activate_subscription_cancels_previous_active_subscription(self):
        now = timezone.now()
        old_subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            starts_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=5),
        )
        new_subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_PENDING,
        )

        activate_subscription(new_subscription, at=now)

        old_subscription.refresh_from_db()
        new_subscription.refresh_from_db()
        self.assertEqual(old_subscription.status, Subscription.STATUS_CANCELLED)
        self.assertEqual(new_subscription.status, Subscription.STATUS_ACTIVE)

    def test_process_successful_payment_is_idempotent(self):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_PENDING,
        )
        payment = Payment.objects.create(
            subscription=subscription,
            user=self.user,
            amount=self.plan.price,
            currency="INR",
            payment_gateway="razorpay",
            gateway_order_id="order_123",
            status=Payment.STATUS_PENDING,
        )
        signature = hmac.new(
            b"test_secret",
            b"order_123|pay_123",
            hashlib.sha256,
        ).hexdigest()

        _, first_subscription, created = process_successful_payment(
            user=self.user,
            subscription_id=subscription.id,
            order_id="order_123",
            payment_id="pay_123",
            signature=signature,
            requested_currency="INR",
        )
        first_subscription.refresh_from_db()
        first_expiry = first_subscription.expires_at

        _, second_subscription, created_again = process_successful_payment(
            user=self.user,
            subscription_id=subscription.id,
            order_id="order_123",
            payment_id="pay_123",
            signature=signature,
            requested_currency="INR",
        )
        second_subscription.refresh_from_db()
        payment.refresh_from_db()

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(payment.gateway_payment_id, "pay_123")
        self.assertEqual(second_subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(second_subscription.expires_at, first_expiry)

    def test_plan_cache_is_invalidated_on_save(self):
        cache.set(PLAN_LIST_CACHE_KEY, [{"id": self.plan.id}])
        self.plan.name = "Starter Plus"
        self.plan.save(update_fields=["name"])
        self.assertIsNone(cache.get(PLAN_LIST_CACHE_KEY))

    def test_payment_serializer_hides_gateway_fields(self):
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_PENDING,
        )
        payment = Payment.objects.create(
            subscription=subscription,
            user=self.user,
            amount=self.plan.price,
            currency="INR",
            payment_gateway="razorpay",
            gateway_order_id="order_123",
            gateway_payment_id="pay_123",
            gateway_signature="secret-signature",
            status=Payment.STATUS_SUCCESS,
        )

        data = PaymentSerializer(payment).data

        self.assertNotIn("gateway_order_id", data)
        self.assertNotIn("gateway_payment_id", data)
        self.assertNotIn("gateway_signature", data)
