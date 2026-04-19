from rest_framework.throttling import ScopedRateThrottle


class CheckoutThrottle(ScopedRateThrottle):
    scope = "subscription_checkout"


class PaymentVerifyThrottle(ScopedRateThrottle):
    scope = "subscription_verify"


class PaymentWebhookThrottle(ScopedRateThrottle):
    scope = "subscription_webhook"
