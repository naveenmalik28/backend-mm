from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import NotificationLog


def _send_notification(user, notification_type, subject, template_name, context):
    html_message = render_to_string(template_name, context)
    send_mail(
        subject=subject,
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True,
    )
    NotificationLog.objects.create(
        user=user,
        notification_type=notification_type,
        subject=subject,
    )


@shared_task
def send_welcome_email(user_id):
    from apps.users.models import CustomUser

    user = CustomUser.objects.filter(pk=user_id).first()
    if not user:
        return
    _send_notification(
        user,
        NotificationLog.TYPE_WELCOME,
        "Welcome to Magnivel Media",
        "welcome.html",
        {"user": user},
    )
