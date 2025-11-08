from django.core.management.base import BaseCommand
from Quizez.models import Category, Subcategory

MAP = {
    'Academic': [
        ('Mathematics', 'Numbers, algebra, geometry and more', 'fas fa-square-root-variable'),
        ('Science', 'Physics, chemistry, biology fundamentals', 'fas fa-flask'),
        ('History', 'Important events and timelines', 'fas fa-landmark'),
    ],
    'Entertainment': [
        ('Movies', 'Cinema, directors, actors and awards', 'fas fa-film'),
        ('Music', 'Genres, artists, and instruments', 'fas fa-music'),
        ('TV & Web', 'Series, streaming and characters', 'fas fa-tv'),
    ],
    'General Knowledge': [
        ('World', 'Countries, capitals, organizations', 'fas fa-globe'),
        ('India', 'Culture, geography, achievements', 'fas fa-flag'),
        ('Current Affairs', 'Recent events and news', 'fas fa-newspaper'),
    ],
}

class Command(BaseCommand):
    help = 'Create a set of initial subcategories for existing categories.'

    def handle(self, *args, **kwargs):
        created = 0
        for cat_name, subs in MAP.items():
            try:
                cat = Category.objects.get(name=cat_name)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Category '{cat_name}' not found; skipping"))
                continue
            for name, desc, icon in subs:
                obj, was_created = Subcategory.objects.get_or_create(
                    category=cat, name=name,
                    defaults={'description': desc, 'icon': icon}
                )
                if was_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"Created {cat_name} / {name}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} subcategories."))
