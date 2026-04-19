import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Plan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, help_text="Short plan tagline")
    duration_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in INR")
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Price in USD")
    currency = models.CharField(max_length=10, default="INR")
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text="Highlight as recommended")
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order on frontend")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "price", "id"]
        indexes = [
            models.Index(fields=["is_active", "sort_order", "price"], name="plan_active_sort_idx"),
        ]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_PENDING = "pending"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_PENDING, "Pending"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "created_at"], name="subscription_user_status_idx"),
            models.Index(fields=["status", "expires_at"], name="subscription_status_expiry_idx"),
            models.Index(fields=["plan", "status"], name="subscription_plan_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="active"),
                name="uniq_active_subscription_per_user",
            ),
            models.CheckConstraint(
                check=Q(starts_at__isnull=True)
                | Q(expires_at__isnull=True)
                | Q(expires_at__gt=F("starts_at")),
                name="subscription_expiry_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

    def activate(self, *, at=None, save=True):
        now = at or timezone.now()
        self.starts_at = now
        self.expires_at = now + timedelta(days=self.plan.duration_days)
        self.status = self.STATUS_ACTIVE
        if save:
            self.save(update_fields=["starts_at", "expires_at", "status", "updated_at"])
        return self


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_gateway = models.CharField(max_length=50, blank=True)
    gateway_order_id = models.CharField(max_length=200, blank=True)
    gateway_payment_id = models.CharField(max_length=200, blank=True)
    gateway_signature = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "created_at"], name="payment_user_status_idx"),
            models.Index(fields=["subscription", "status", "created_at"], name="payment_sub_status_idx"),
            models.Index(fields=["payment_gateway", "created_at"], name="payment_gateway_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["payment_gateway", "gateway_order_id"],
                condition=~Q(gateway_order_id=""),
                name="uniq_payment_gateway_order_id",
            ),
            models.UniqueConstraint(
                fields=["payment_gateway", "gateway_payment_id"],
                condition=~Q(gateway_payment_id=""),
                name="uniq_payment_gateway_payment_id",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.status}"

# Create your models here.
