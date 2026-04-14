from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.tasks import send_welcome_email

from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def trigger_welcome_email(sender, instance, created, **kwargs):
    if created:
        send_welcome_email.delay(str(instance.id))

