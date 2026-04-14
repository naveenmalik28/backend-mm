import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.articles.models import Tag
from django.template.defaultfilters import slugify

tags = [
    "Machine Learning",
    "Deep Learning",
    "Genetics",
    "Startups",
    "Venture Capital",
    "Physics",
    "Chemistry"
]

for name in tags:
    slug = slugify(name)
    Tag.objects.get_or_create(name=name, defaults={'slug': slug})

print("Test tags created.")
