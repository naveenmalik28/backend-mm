from django.contrib import admin

from .models import Payment, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_days", "price", "price_usd", "sort_order", "is_popular", "is_active")
    list_editable = ("price", "price_usd", "sort_order", "is_popular", "is_active")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "is_popular")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "starts_at", "expires_at")
    list_filter = ("status", "plan")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "payment_gateway", "status", "created_at")
    list_filter = ("status", "payment_gateway")
    search_fields = ("user__email", "gateway_payment_id")
    readonly_fields = ("gateway_order_id", "gateway_payment_id", "gateway_signature")


# Register your models here.
