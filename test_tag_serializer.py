import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.articles.serializers import TagSerializer
from apps.articles.models import Tag

tag = Tag.objects.create(name="Test Tag", slug="test-tag")
serializer = TagSerializer(tag)
try:
    print(serializer.data)
except Exception as e:
    print(f"Error: {e}")

tag.delete()
