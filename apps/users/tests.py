from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from kombu.exceptions import OperationalError as KombuOperationalError

from apps.subscriptions.models import Payment, Plan, Subscription


User = get_user_model()


class WelcomeEmailSignalTests(TestCase):
    def test_regular_user_creation_queues_welcome_email_after_commit(self):
        with patch("apps.users.signals.transaction.on_commit", side_effect=lambda callback: callback()) as mocked_on_commit, patch(
            "apps.users.signals.send_welcome_email.delay"
        ) as mocked_delay:
            user = User.objects.create_user(
                email="reader@example.com",
                username="reader",
                password="password123",
            )

        mocked_on_commit.assert_called_once()
        mocked_delay.assert_called_once_with(str(user.pk))

    def test_superuser_creation_does_not_queue_welcome_email(self):
        with patch("apps.users.signals.transaction.on_commit") as mocked_on_commit, patch(
            "apps.users.signals.send_welcome_email.delay"
        ) as mocked_delay:
            User.objects.create_superuser(
                email="admin@example.com",
                username="admin",
                password="password123",
            )

        mocked_on_commit.assert_not_called()
        mocked_delay.assert_not_called()

    def test_user_creation_succeeds_when_broker_is_unavailable(self):
        with patch("apps.users.signals.transaction.on_commit", side_effect=lambda callback: callback()), patch(
            "apps.users.signals.send_welcome_email.delay",
            side_effect=KombuOperationalError("broker unavailable"),
        ):
            user = User.objects.create_user(
                email="offline@example.com",
                username="offline",
                password="password123",
            )

        self.assertEqual(user.email, "offline@example.com")


class AdminRevenueApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="password123",
        )
        self.client.force_authenticate(self.admin)
        self.plan = Plan.objects.create(
            name="Pro",
            slug="pro",
            duration_days=30,
            price=Decimal("999.00"),
            price_usd=Decimal("19.00"),
            is_active=True,
        )

    def test_admin_summary_includes_revenue_totals(self):
        user = User.objects.create_user(
            email="member@example.com",
            username="member",
            password="password123",
        )
        subscription = Subscription.objects.create(
            user=user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
        )
        Payment.objects.create(
            subscription=subscription,
            user=user,
            amount=Decimal("999.00"),
            currency="INR",
            payment_gateway="razorpay",
            gateway_order_id="order_inr",
            gateway_payment_id="pay_inr",
            status=Payment.STATUS_SUCCESS,
        )
        Payment.objects.create(
            subscription=subscription,
            user=user,
            amount=Decimal("19.00"),
            currency="USD",
            payment_gateway="stripe",
            gateway_order_id="order_usd",
            gateway_payment_id="pay_usd",
            status=Payment.STATUS_SUCCESS,
        )

        response = self.client.get("/api/auth/admin/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["successful_payments"], 2)
        self.assertEqual(Decimal(str(response.data["successful_revenue_inr"])), Decimal("999.00"))
        self.assertEqual(Decimal(str(response.data["successful_revenue_usd"])), Decimal("19.00"))

    def test_admin_subscription_and_payment_lists_are_paginated(self):
        user = User.objects.create_user(
            email="member2@example.com",
            username="member2",
            password="password123",
        )
        subscriptions = [
            Subscription(user=user, plan=self.plan, status=Subscription.STATUS_PENDING)
            for _ in range(30)
        ]
        Subscription.objects.bulk_create(subscriptions)
        created_subscriptions = list(Subscription.objects.order_by("created_at"))
        Payment.objects.bulk_create(
            [
                Payment(
                    subscription=subscription,
                    user=user,
                    amount=Decimal("999.00"),
                    currency="INR",
                    payment_gateway="razorpay",
                    gateway_order_id=f"order_{index}",
                    status=Payment.STATUS_PENDING,
                )
                for index, subscription in enumerate(created_subscriptions)
            ]
        )

        subscription_response = self.client.get("/api/auth/admin/subscriptions/")
        payment_response = self.client.get("/api/auth/admin/payments/")

        self.assertEqual(subscription_response.status_code, 200)
        self.assertIn("results", subscription_response.data)
        self.assertEqual(subscription_response.data["count"], 30)
        self.assertEqual(len(subscription_response.data["results"]), 25)

        self.assertEqual(payment_response.status_code, 200)
        self.assertIn("results", payment_response.data)
        self.assertEqual(payment_response.data["count"], 30)
        self.assertEqual(len(payment_response.data["results"]), 25)
