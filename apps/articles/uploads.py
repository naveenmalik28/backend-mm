import os
from pathlib import Path
from uuid import uuid4

import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


def is_cloudinary_configured():
    cloudinary_settings = getattr(settings, "CLOUDINARY_STORAGE", {}) or {}
    if all(
        cloudinary_settings.get(key)
        for key in ("CLOUD_NAME", "API_KEY", "API_SECRET")
    ):
        return True

    if os.environ.get("CLOUDINARY_URL"):
        return True

    return all(
        os.environ.get(key)
        for key in (
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET",
        )
    )


def validate_image_file(image_file):
    content_type = getattr(image_file, "content_type", "") or ""
    if content_type and not content_type.startswith("image/"):
        raise ValueError("Only image uploads are allowed.")

    if image_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image must be 10 MB or smaller.")


def _normalized_filename(filename):
    suffix = Path(filename or "").suffix.lower()
    return f"{uuid4().hex}{suffix}"


def upload_article_image(image_file):
    validate_image_file(image_file)

    if is_cloudinary_configured():
        try:
            result = cloudinary.uploader.upload(
                image_file,
                folder="articles/covers",
                resource_type="image",
                use_filename=True,
                unique_filename=True,
                overwrite=False,
            )
        except CloudinaryError as exc:
            raise RuntimeError(f"Cloudinary upload failed: {exc}") from exc

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "storage": "cloudinary",
        }

    if not settings.DEBUG:
        raise ImproperlyConfigured(
            "Cloudinary is required for image uploads in production. "
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and "
            "CLOUDINARY_API_SECRET in Railway."
        )

    file_name = default_storage.save(
        f"articles/covers/{_normalized_filename(getattr(image_file, 'name', 'image'))}",
        image_file,
    )
    return {
        "url": default_storage.url(file_name),
        "public_id": file_name,
        "storage": "local",
    }
