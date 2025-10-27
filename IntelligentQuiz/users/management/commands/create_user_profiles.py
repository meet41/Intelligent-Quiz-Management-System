from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile

class Command(BaseCommand):
    help = 'Creates user profiles for existing users'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        count = 0
        for user in users:
            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {count} profiles for existing users'
            )
        )