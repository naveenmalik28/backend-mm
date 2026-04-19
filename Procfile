web: gunicorn config.wsgi:application --env DJANGO_SETTINGS_MODULE=config.settings.production --bind 0.0.0.0:${PORT:-8000} --log-file -
