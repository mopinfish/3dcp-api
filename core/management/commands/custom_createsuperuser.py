import os
from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError
from django.contrib.auth import get_user_model

class Command(createsuperuser.Command):
    help = 'Create a superuser without prompts'

    def handle(self, *args, **options):
        username = os.environ.get('SUPERUSER_NAME', 'admin')
        email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('SUPERUSER_PASSWORD', 'admin')

        if not username or not email or not password:
            raise CommandError('You must specify username, email, and password')

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write('Username already exists')
        else:
            user = User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully'))
