import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.articles.serializers import ArticleSerializer
from apps.users.models import CustomUser
from apps.articles.models import Category, Tag

user = CustomUser.objects.first()
category = Category.objects.first()
tag, _ = Tag.objects.get_or_create(name="Test Tag", slug="test-tag")

data = {
    "title": "Test Article",
    "content": "Test content",
    "category_id": category.id if category else None,
    "tag_ids": [tag.id],
    "status": "draft"
}

serializer = ArticleSerializer(data=data)
print("Is valid:", serializer.is_valid())
if not serializer.is_valid():
    print("Errors:", serializer.errors)
else:
    article = serializer.save(author=user)
    print("Article created:", article.id)
    print("Tags assigned:", article.tags.all())
    article.delete()
