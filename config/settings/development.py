from .base import *  # noqa: F401,F403
from .database import configured_postgres_database

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

postgres_database = configured_postgres_database(
    conn_max_age=600,
    conn_health_checks=True,
)

if postgres_database:
    DATABASES = {
        "default": postgres_database
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
CELERY_TASK_ALWAYS_EAGER = True
