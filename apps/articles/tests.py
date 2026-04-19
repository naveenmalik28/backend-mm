from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Article, Category, Tag

User = get_user_model()


class CategoryTagApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="password123",
            is_staff=True,
        )
        self.author = User.objects.create_user(
            email="writer@example.com",
            username="writer",
            password="password123",
        )
        self.category = Category.objects.create(
            name="Technology & Innovation",
            slug="technology-innovation",
            description="The bleeding edge of tech.",
        )
        self.tag = Tag.objects.create(name="AI", slug="ai")

    def test_category_list_is_public(self):
        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], self.category.name)
        self.assertEqual(response.data[0]["slug"], self.category.slug)

    def test_admin_can_create_update_and_delete_category(self):
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            reverse("category-list"),
            {"name": "Science & Research", "description": "Peer-reviewed and breakthrough science."},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name="Science & Research").exists())

        category_id = create_response.data["id"]
        update_response = self.client.put(
            reverse("category-detail", args=[category_id]),
            {
                "name": "Science and Research",
                "slug": "science-research",
                "description": "Updated description",
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["slug"], "science-research")

        delete_response = self.client.delete(reverse("category-detail", args=[category_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category_id).exists())

    def test_authenticated_user_can_create_tag_while_only_admin_can_delete(self):
        self.client.force_authenticate(self.author)
        create_response = self.client.post(reverse("tag-list"), {"name": "Robotics"}, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["slug"], "robotics")

        tag_id = create_response.data["id"]
        delete_response = self.client.delete(reverse("tag-detail", args=[tag_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        delete_response = self.client.delete(reverse("tag-detail", args=[tag_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_article_create_saves_category_tags_and_public_filtering_works(self):
        self.client.force_authenticate(self.admin)

        create_response = self.client.post(
            reverse("article-list-create"),
            {
                "title": "Future of Applied AI",
                "excerpt": "How AI changes product teams.",
                "content": "A fairly long article body about AI systems.",
                "status": Article.STATUS_PUBLISHED,
                "category_id": self.category.id,
                "tag_ids": [self.tag.id],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        article_id = create_response.data["id"]

        article = Article.objects.get(pk=article_id)
        self.assertEqual(article.category_id, self.category.id)
        self.assertEqual(list(article.tags.values_list("id", flat=True)), [self.tag.id])

        self.client.force_authenticate(user=None)
        category_response = self.client.get(reverse("article-list-create"), {"category": self.category.slug})
        tag_response = self.client.get(reverse("article-list-create"), {"tag": self.tag.slug})

        self.assertEqual(category_response.status_code, status.HTTP_200_OK)
        self.assertEqual(category_response.data["count"], 1)
        self.assertEqual(tag_response.data["count"], 1)

    def test_article_create_with_cover_image_file_uploads_to_cloudinary_and_saves_url(self):
        self.client.force_authenticate(self.admin)

        with patch("apps.articles.serializers.upload_article_image") as mocked_upload:
            mocked_upload.return_value = {
                "url": "https://res.cloudinary.com/demo/image/upload/articles/covers/test-image.jpg",
                "public_id": "articles/covers/test-image",
                "storage": "cloudinary",
            }
            response = self.client.post(
                reverse("article-list-create"),
                {
                    "title": "Cloudinary-backed article",
                    "excerpt": "Cover image should be stored as a URL.",
                    "content": "A long-form story with a direct file upload.",
                    "status": Article.STATUS_DRAFT,
                    "category_id": self.category.id,
                    "tag_ids": [self.tag.id],
                    "cover_image_file": SimpleUploadedFile(
                        "cover.jpg",
                        b"fake-image-bytes",
                        content_type="image/jpeg",
                    ),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["cover_image"],
            "https://res.cloudinary.com/demo/image/upload/articles/covers/test-image.jpg",
        )
        article = Article.objects.get(pk=response.data["id"])
        self.assertEqual(
            article.cover_image,
            "https://res.cloudinary.com/demo/image/upload/articles/covers/test-image.jpg",
        )
        mocked_upload.assert_called_once()

    def test_article_update_with_cover_image_file_replaces_stored_cover_image_url(self):
        article = Article.objects.create(
            author=self.author,
            category=self.category,
            title="Existing article",
            excerpt="Before the new image upload.",
            content="Existing content body.",
            cover_image="https://example.com/original-cover.jpg",
        )
        article.tags.add(self.tag)

        self.client.force_authenticate(self.author)

        with patch("apps.articles.serializers.upload_article_image") as mocked_upload:
            mocked_upload.return_value = {
                "url": "https://res.cloudinary.com/demo/image/upload/articles/covers/updated-image.jpg",
                "public_id": "articles/covers/updated-image",
                "storage": "cloudinary",
            }
            response = self.client.patch(
                reverse("article-detail", args=[article.pk]),
                {
                    "cover_image_file": SimpleUploadedFile(
                        "updated-cover.jpg",
                        b"fake-image-bytes",
                        content_type="image/jpeg",
                    ),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["cover_image"],
            "https://res.cloudinary.com/demo/image/upload/articles/covers/updated-image.jpg",
        )
        article.refresh_from_db()
        self.assertEqual(
            article.cover_image,
            "https://res.cloudinary.com/demo/image/upload/articles/covers/updated-image.jpg",
        )
        mocked_upload.assert_called_once()

    def test_authenticated_user_can_upload_article_image_to_cloudinary(self):
        self.client.force_authenticate(self.author)

        with patch("apps.articles.uploads.is_cloudinary_configured", return_value=True), patch(
            "apps.articles.uploads.cloudinary.uploader.upload",
            return_value={
                "secure_url": "https://res.cloudinary.com/demo/image/upload/articles/covers/test-image.jpg",
                "public_id": "articles/covers/test-image",
            },
        ) as mocked_upload:
            response = self.client.post(
                reverse("article-upload-image"),
                {"image": SimpleUploadedFile("cover.jpg", b"fake-image-bytes", content_type="image/jpeg")},
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["url"],
            "https://res.cloudinary.com/demo/image/upload/articles/covers/test-image.jpg",
        )
        self.assertEqual(response.data["storage"], "cloudinary")
        mocked_upload.assert_called_once()

    def test_production_upload_requires_cloudinary_configuration(self):
        self.client.force_authenticate(self.author)

        with patch("apps.articles.uploads.is_cloudinary_configured", return_value=False), patch(
            "apps.articles.uploads.settings.DEBUG",
            False,
        ):
            response = self.client.post(
                reverse("article-upload-image"),
                {"image": SimpleUploadedFile("cover.jpg", b"fake-image-bytes", content_type="image/jpeg")},
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Cloudinary is required", response.data["error"])

    def test_upload_rejects_missing_image(self):
        self.client.force_authenticate(self.author)

        response = self.client.post(reverse("article-upload-image"), {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "No image provided")
