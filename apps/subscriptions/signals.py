from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Plan
from .services import invalidate_plan_cache


@receiver(post_save, sender=Plan)
@receiver(post_delete, sender=Plan)
def clear_plan_cache(**kwargs):
    invalidate_plan_cache()
