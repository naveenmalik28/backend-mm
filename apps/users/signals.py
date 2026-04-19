import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from kombu.exceptions import OperationalError as KombuOperationalError

from apps.notifications.tasks import send_welcome_email

from .models import CustomUser

logger = logging.getLogger(__name__)


def _queue_welcome_email(user_id):
    try:
        send_welcome_email.delay(str(user_id))
    except (KombuOperationalError, ConnectionRefusedError, OSError):
        logger.warning("Skipping welcome email for user %s because the task broker is unavailable.", user_id)


@receiver(post_save, sender=CustomUser)
def trigger_welcome_email(sender, instance, created, **kwargs):
    if not created or instance.is_staff or instance.is_superuser:
        return

    transaction.on_commit(lambda: _queue_welcome_email(instance.pk))
