from urllib.parse import quote_plus

import dj_database_url
from decouple import config
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403


def _csv_env(name):
    return [item.strip() for item in config(name, default="").split(",") if item.strip()]


def _configured_values(*names):
    return [value for value in (config(name, default="").strip() for name in names) if value]


def _https_origin(value):
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _cloudinary_config():
    values = {
        "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default="").strip(),
        "API_KEY": config("CLOUDINARY_API_KEY", default="").strip(),
        "API_SECRET": config("CLOUDINARY_API_SECRET", default="").strip(),
    }
    return values if all(values.values()) else None


def _database_url():
    configured_urls = _configured_values(
        "DATABASE_URL",
        "DATABASE_PRIVATE_URL",
        "DATABASE_PUBLIC_URL",
        "POSTGRES_URL",
        "POSTGRESQL_URL",
    )
    if configured_urls:
        return configured_urls[0]

    host = config("PGHOST", default="").strip()
    name = config("PGDATABASE", default="").strip()
    user = config("PGUSER", default="").strip()
    password = config("PGPASSWORD", default="").strip()
    port = config("PGPORT", default="5432").strip() or "5432"

    if all([host, name, user, password]):
        return (
            "postgresql://"
            f"{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{quote_plus(name)}"
        )

    raise ImproperlyConfigured(
        "Database is not configured for production. Set DATABASE_URL "
        "(preferred), DATABASE_PRIVATE_URL, DATABASE_PUBLIC_URL, POSTGRES_URL, "
        "POSTGRESQL_URL, or the PGHOST/PGDATABASE/PGUSER/PGPASSWORD env vars."
    )


DEBUG = False

ALLOWED_HOSTS = list(
    dict.fromkeys(
        [
            ".railway.app",
            ".up.railway.app",
            *_csv_env("ALLOWED_HOSTS"),
            *_configured_values("RAILWAY_PUBLIC_DOMAIN", "RAILWAY_PRIVATE_DOMAIN", "CUSTOM_DOMAIN"),
        ]
    )
)

DATABASES = {
    "default": dj_database_url.parse(
        _database_url(),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

CORS_ALLOWED_ORIGINS = list(
    dict.fromkeys(_configured_values("FRONTEND_URL", "ADMIN_FRONTEND_URL"))
)

CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(
        [
            *CORS_ALLOWED_ORIGINS,
            *[
                _https_origin(value)
                for value in _configured_values("RAILWAY_PUBLIC_DOMAIN", "CUSTOM_DOMAIN")
            ],
        ]
    )
)

_cloudinary = _cloudinary_config()
if _cloudinary:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    CLOUDINARY_STORAGE = _cloudinary

EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="").strip()
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="").strip()

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
