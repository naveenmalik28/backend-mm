from django.contrib import admin

from .models import Article, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "is_featured", "view_count", "published_at")
    list_filter = ("status", "is_featured", "category", "created_at")
    search_fields = ("title", "excerpt", "author__email")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"
    actions = ("make_published", "make_archived", "mark_featured")
    list_editable = ("is_featured", "status")

    @admin.action(description="Mark selected articles as Published")
    def make_published(self, request, queryset):
        queryset.update(status=Article.STATUS_PUBLISHED)

    @admin.action(description="Mark selected articles as Archived")
    def make_archived(self, request, queryset):
        queryset.update(status=Article.STATUS_ARCHIVED)

    @admin.action(description="Mark as Featured")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)


# Register your models here.
