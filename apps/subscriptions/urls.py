from django.urls import path

from .views import (
    CancelSubscriptionView,
    CheckoutView,
    CurrentSubscriptionView,
    PaymentVerifyView,
    PlanListView,
    RazorpayWebhookView,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("subscriptions/checkout/", CheckoutView.as_view(), name="subscription-checkout"),
    path("subscriptions/verify/", PaymentVerifyView.as_view(), name="subscription-verify"),
    path("subscriptions/webhooks/razorpay/", RazorpayWebhookView.as_view(), name="subscription-razorpay-webhook"),
    path("subscriptions/my/", CurrentSubscriptionView.as_view(), name="subscription-current"),
    path("subscriptions/<uuid:pk>/cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
]
