import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.articles.models import Tag

tags = Tag.objects.all()
print(f"Total tags in DB: {tags.count()}")
for tag in tags:
    print(tag.name)
