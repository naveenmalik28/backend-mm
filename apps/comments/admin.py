from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("article", "author", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("article__title", "author__email", "body")


# Register your models here.
