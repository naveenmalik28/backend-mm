from django.urls import path

from .views import CancelSubscriptionView, CheckoutView, CurrentSubscriptionView, PaymentVerifyView, PlanListView

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("subscriptions/checkout/", CheckoutView.as_view(), name="subscription-checkout"),
    path("subscriptions/verify/", PaymentVerifyView.as_view(), name="subscription-verify"),
    path("subscriptions/my/", CurrentSubscriptionView.as_view(), name="subscription-current"),
    path("subscriptions/<uuid:pk>/cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
]
