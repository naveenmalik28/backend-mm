import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.articles.models import Category
from django.template.defaultfilters import slugify

categories = [
    "Artificial Intelligence",
    "Biomedical & Health",
    "Business & Startups",
    "Education & Careers",
    "Science & Research",
    "Society & Culture",
    "Technology & Innovation"
]

for name in categories:
    slug = slugify(name)
    cat, created = Category.objects.get_or_create(name=name, defaults={'slug': slug})
    if created:
        print(f"Created category: {name}")
    else:
        print(f"Category already exists: {name}")

print("Done.")
