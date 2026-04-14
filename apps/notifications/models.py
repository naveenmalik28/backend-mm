from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    TYPE_WELCOME = "welcome"
    TYPE_SUBSCRIPTION = "subscription_confirmed"
    TYPE_ARTICLE = "article_published"
    TYPE_CHOICES = (
        (TYPE_WELCOME, "Welcome"),
        (TYPE_SUBSCRIPTION, "Subscription Confirmed"),
        (TYPE_ARTICLE, "Article Published"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.notification_type}"

# Create your models here.
