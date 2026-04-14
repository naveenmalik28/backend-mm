from django.core.management.base import BaseCommand
from apps.articles.models import Category

NEW_CATEGORIES = [
    {"name": "Technology & Innovation", "slug": "technology-innovation", "description": "The bleeding edge of tech and modern workflow innovation."},
    {"name": "Artificial Intelligence", "slug": "artificial-intelligence", "description": "Neural networks, automation, and the future of AGI."},
    {"name": "Science & Research", "slug": "science-research", "description": "Breakthrough papers, peer-reviewed analysis, and scientific discoveries."},
    {"name": "Biomedical & Health", "slug": "biomedical-health", "description": "Biotech startups, medical advancements, and longevity research."},
    {"name": "Business & Startups", "slug": "business-startups", "description": "Venture capital, bootstrapping, and enterprise strategy."},
    {"name": "Education & Careers", "slug": "education-careers", "description": "The future of learning and the global workforce."},
    {"name": "Society & Culture", "slug": "society-culture", "description": "Anthropology, philosophy, and modern cultural shifts."},
]

class Command(BaseCommand):
    help = 'Seeds premium global categories into the database'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding premium global categories...")
        
        # 1. Ensure seed data is fully synced, not just created once.
        for cat_data in NEW_CATEGORIES:
            category = Category.objects.filter(slug=cat_data["slug"]).first()
            if category is None:
                category = Category.objects.create(**cat_data)
                self.stdout.write(self.style.SUCCESS(f"Created: {category.name}"))
            else:
                updates = {}
                if category.name != cat_data["name"]:
                    updates["name"] = cat_data["name"]
                if category.description != cat_data["description"]:
                    updates["description"] = cat_data["description"]
                if updates:
                    for field, value in updates.items():
                        setattr(category, field, value)
                    category.save(update_fields=[*updates.keys(), "slug"])
                    self.stdout.write(self.style.SUCCESS(f"Updated: {category.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Exists: {category.name}"))

        # 2. Cleanup unused old generic categories so they don't pollute the UI
        allowed_slugs = [c["slug"] for c in NEW_CATEGORIES]
        old_cats = Category.objects.exclude(slug__in=allowed_slugs)
        
        if old_cats.exists():
            self.stdout.write(f"Found {old_cats.count()} old categories. Migrating their articles to 'Society & Culture' and deleting...")
            fallback = Category.objects.get(slug="society-culture")
            
            for old in old_cats:
                # Move articles to fallback
                old.articles.update(category=fallback)
                name = old.name
                old.delete()
                self.stdout.write(f"   Deleted legacy category: {name}")

        self.stdout.write(self.style.SUCCESS("Premium categories successfully synced!"))
