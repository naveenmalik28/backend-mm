from celery import shared_task

from .services import expire_due_subscriptions


@shared_task
def expire_stale_subscriptions(batch_size=1000):
    return expire_due_subscriptions(batch_size=batch_size)
