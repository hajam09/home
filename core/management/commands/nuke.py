from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Completely deletes ALL data from the Django database (including auth, sessions, admin logs).'

    def log(self, value):
        self.stdout.write(f'\n{value}\n')

    def handle(self, *args, **kwargs):
        self.log('Nuking database using Django flush...')
        call_command('flush', interactive=False)
        self.log('Database fully reset.')
