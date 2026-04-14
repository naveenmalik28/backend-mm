from django.conf import settings


def storage_backend_name():
    return getattr(settings, "DEFAULT_FILE_STORAGE", "django.core.files.storage.FileSystemStorage")

