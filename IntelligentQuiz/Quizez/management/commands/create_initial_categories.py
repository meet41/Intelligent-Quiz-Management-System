from django.core.management.base import BaseCommand
from Quizez.models import Category

class Command(BaseCommand):
    help = 'Create initial quiz categories'

    def handle(self, *args, **kwargs):
        categories = [
            {
                'name': 'Academic',
                'icon': 'fas fa-graduation-cap',
                'description': 'Educational quizzes covering various academic subjects'
            },
            {
                'name': 'Entertainment',
                'icon': 'fas fa-film',
                'description': 'Fun quizzes about movies, music, TV shows, and pop culture'
            },
            {
                'name': 'General Knowledge',
                'icon': 'fas fa-brain',
                'description': 'Test your knowledge of various general topics'
            },
            {
                'name': 'Science & Technology',
                'icon': 'fas fa-microscope',
                'description': 'Explore the world of science and modern technology'
            },
            {
                'name': 'Sports',
                'icon': 'fas fa-futbol',
                'description': 'Challenge yourself with sports trivia'
            }
        ]

        for category_data in categories:
            Category.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'icon': category_data['icon'],
                    'description': category_data['description']
                }
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created category "{category_data["name"]}"')
            )