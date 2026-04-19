from urllib.parse import quote_plus

import dj_database_url
from decouple import config
from django.core.exceptions import ImproperlyConfigured


DATABASE_CONFIGURATION_ERROR = (
    "Database is not configured. Set DATABASE_URL (preferred), "
    "DATABASE_PRIVATE_URL, DATABASE_PUBLIC_URL, POSTGRES_URL, "
    "POSTGRESQL_URL, or the PGHOST/PGDATABASE/PGUSER/PGPASSWORD env vars."
)


def configured_database_url():
    configured_urls = [
        value
        for value in (
            config("DATABASE_URL", default="").strip(),
            config("DATABASE_PRIVATE_URL", default="").strip(),
            config("DATABASE_PUBLIC_URL", default="").strip(),
            config("POSTGRES_URL", default="").strip(),
            config("POSTGRESQL_URL", default="").strip(),
        )
        if value
    ]
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

    return ""


def require_database_url():
    database_url = configured_database_url()
    if database_url:
        return database_url
    raise ImproperlyConfigured(DATABASE_CONFIGURATION_ERROR)


def configured_postgres_database(**kwargs):
    database_url = configured_database_url()
    if not database_url:
        return None
    return dj_database_url.parse(database_url, **kwargs)
