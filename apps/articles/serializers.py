from django.db.models import Q
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.users.serializers import UserSerializer

from .models import Article, Category, Tag, SiteSettings
from .uploads import upload_article_image


class ImageUploadUnavailable(APIException):
    status_code = 503
    default_detail = "Image uploads are unavailable right now."
    default_code = "image_upload_unavailable"


class ImageUploadFailed(APIException):
    status_code = 502
    default_detail = "Image upload failed."
    default_code = "image_upload_failed"


class CategorySerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "created_at", "article_count")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }


class TagSerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Tag
        fields = ("id", "name", "slug", "article_count")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }


class ArticleSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(read_only=True, many=True)
    cover_image_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        queryset=Tag.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Article
        fields = (
            "id",
            "author",
            "category",
            "category_id",
            "tags",
            "tag_ids",
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "cover_image_file",
            "status",
            "is_featured",
            "view_count",
            "read_time",
            "published_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "view_count", "read_time", "published_at", "created_at", "updated_at")

    def _attach_uploaded_cover_image(self, validated_data):
        image_file = validated_data.pop("cover_image_file", None)
        if not image_file:
            return

        try:
            upload_result = upload_article_image(image_file)
        except ValueError as exc:
            raise serializers.ValidationError({"cover_image_file": [str(exc)]}) from exc
        except ImproperlyConfigured as exc:
            raise ImageUploadUnavailable(str(exc)) from exc
        except RuntimeError as exc:
            raise ImageUploadFailed(str(exc)) from exc

        validated_data["cover_image"] = upload_result["url"]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        self._attach_uploaded_cover_image(validated_data)
        article = Article.objects.create(**validated_data)
        if tags:
            article.tags.set(tags)
        return article

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        self._attach_uploaded_cover_image(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance


class ArticleDetailSerializer(ArticleSerializer):
    related_articles = serializers.SerializerMethodField()

    class Meta(ArticleSerializer.Meta):
        fields = ArticleSerializer.Meta.fields + ("related_articles",)

    def get_related_articles(self, obj):
        queryset = (
            Article.objects.filter(status=Article.STATUS_PUBLISHED)
            .exclude(id=obj.id)
            .select_related("author", "category")
            .prefetch_related("tags")
        )
        if obj.category_id:
            tag_ids = list(obj.tags.values_list("id", flat=True))
            queryset = queryset.filter(
                Q(category_id=obj.category_id) | Q(tags__in=tag_ids)
            ).distinct()

        related = queryset.order_by("-view_count", "-published_at")[:3]
        return ArticleSerializer(related, many=True).data


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = (
            "site_name",
            "tagline",
            "description",
            "about_text",
            "twitter_url",
            "github_url",
            "linkedin_url",
            "instagram_url",
            "default_meta_description",
            "default_og_image",
            "contact_email",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class AdminCommentSerializer(serializers.Serializer):
    """Read-only serializer for admin comment listing."""
    id = serializers.UUIDField()
    body = serializers.CharField()
    is_approved = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    author_email = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    article_title = serializers.SerializerMethodField()
    article_id = serializers.SerializerMethodField()

    def get_author_email(self, obj):
        return obj.author.email if obj.author else ""

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author else ""

    def get_article_title(self, obj):
        return obj.article.title if obj.article else ""

    def get_article_id(self, obj):
        return str(obj.article.id) if obj.article else ""
