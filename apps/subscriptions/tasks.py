from celery import shared_task
from django.utils import timezone

from .models import Subscription


@shared_task
def expire_stale_subscriptions():
    return Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE,
        expires_at__lt=timezone.now(),
    ).update(status=Subscription.STATUS_EXPIRED)

