from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "subject", "created_at")
    list_filter = ("notification_type", "created_at")
    search_fields = ("user__email", "subject")


# Register your models here.
