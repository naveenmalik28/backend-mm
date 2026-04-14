import re
import uuid

from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, db_index=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, db_index=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Article(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="articles")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    cover_image = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    read_time = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def _generate_unique_slug(self):
        base_slug = slugify(self.title)[:300] or f"article-{self.pk}"
        slug = base_slug
        suffix = 1
        while Article.objects.exclude(pk=self.pk).filter(slug=slug).exists():
            slug = f"{base_slug[:310]}-{suffix}"
            suffix += 1
        return slug

    def _calculate_read_time(self):
        plain_text = re.sub(r"<[^>]+>", " ", self.content or "")
        word_count = len([word for word in plain_text.split() if word])
        self.read_time = max(1, (word_count + 199) // 200) if word_count else 1

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        self._calculate_read_time()
        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        if self.status != self.STATUS_PUBLISHED:
            self.published_at = None
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """Singleton model for site-wide configuration."""
    site_name = models.CharField(max_length=200, default="Magnivel Media")
    tagline = models.CharField(max_length=300, blank=True, default="A global thought-sharing publication")
    description = models.TextField(blank=True, default="")
    about_text = models.TextField(blank=True, default="")
    # Social links
    twitter_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    # SEO defaults
    default_meta_description = models.TextField(blank=True, default="")
    default_og_image = models.URLField(blank=True, default="")
    # Contact
    contact_email = models.EmailField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
