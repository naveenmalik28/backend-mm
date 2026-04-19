from django.core.management.base import BaseCommand
from apps.articles.models import Category

NEW_CATEGORIES = [
    {"name": "AI", "slug": "ai", "description": "Artificial intelligence strategy, tools, models, and real-world adoption."},
    {"name": "Technology", "slug": "technology", "description": "Emerging technology, product shifts, and the systems shaping modern life."},
    {"name": "Software Development", "slug": "software-development", "description": "Engineering practice, developer tooling, architecture, and shipping software well."},
    {"name": "Business & Startups", "slug": "business-startups", "description": "Founders, strategy, venture building, operations, and growth."},
    {"name": "Digital Marketing", "slug": "digital-marketing", "description": "Search, content, social, demand generation, and digital brand building."},
    {"name": "Data Science", "slug": "data-science", "description": "Analytics, machine learning workflows, experimentation, and data-driven decision-making."},
    {"name": "Cybersecurity", "slug": "cybersecurity", "description": "Security trends, privacy, cyber risk, and digital resilience."},
    {"name": "Health", "slug": "health", "description": "Health innovation, biomedical progress, care systems, and public health."},
    {"name": "Science", "slug": "science", "description": "Scientific discovery, research breakthroughs, and evidence-based analysis."},
    {"name": "Education", "slug": "education", "description": "Learning, careers, skills, and the future of education."},
    {"name": "Society", "slug": "society", "description": "Culture, ethics, public life, and the ideas influencing society."},
]

LEGACY_CATEGORY_REDIRECTS = {
    "artificial-intelligence": "ai",
    "technology-innovation": "technology",
    "science-research": "science",
    "biomedical-health": "health",
    "business-startups": "business-startups",
    "education-careers": "education",
    "society-culture": "society",
}

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

        # 2. Migrate known legacy categories into the new taxonomy.
        for old_slug, target_slug in LEGACY_CATEGORY_REDIRECTS.items():
            if old_slug == target_slug:
                continue

            legacy_category = Category.objects.filter(slug=old_slug).first()
            target_category = Category.objects.filter(slug=target_slug).first()
            if not legacy_category or not target_category:
                continue

            migrated_count = legacy_category.articles.update(category=target_category)
            name = legacy_category.name
            legacy_category.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrated {migrated_count} articles from '{name}' to '{target_category.name}'."
                )
            )

        # 3. Cleanup unused old generic categories so they don't pollute the UI.
        allowed_slugs = [c["slug"] for c in NEW_CATEGORIES]
        old_cats = Category.objects.exclude(slug__in=allowed_slugs)
        
        if old_cats.exists():
            self.stdout.write(f"Found {old_cats.count()} old categories. Migrating their articles to 'Society' and deleting...")
            fallback = Category.objects.get(slug="society")
            
            for old in old_cats:
                old.articles.update(category=fallback)
                name = old.name
                old.delete()
                self.stdout.write(f"   Deleted legacy category: {name}")

        self.stdout.write(self.style.SUCCESS("Premium categories successfully synced!"))
