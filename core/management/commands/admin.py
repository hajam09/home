from decouple import config
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Creates admin account'

    def log(self, value):
        self.stdout.write(f'\n{value}\n')

    def handle(self, *args, **kwargs):
        self.log('Starting creation of admin user...')

        try:
            user = User(
                username=config('ADMIN_USERNAME', cast=str),
                email=config('ADMIN_EMAIL', cast=str),
                first_name=config('ADMIN_FIRST_NAME', cast=str),
                last_name=config('ADMIN_LAST_NAME', cast=str),
                is_staff=True,
                is_active=True,
                is_superuser=True,
            )
            user.set_password(config('ADMIN_PASSWORD', cast=str))
            user.save()
            self.log('Default superuser created successfully.')

        except IntegrityError:
            self.log('Admin user already exists. Skipping creation.')
        except Exception as e:
            self.log(f'Unexpected error: {e}')

        self.log(f'Admin user setup complete.')
