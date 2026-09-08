from datetime import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send DB backup email, then run event reminders until midnight'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"🚀 Daily task started at {datetime.now().strftime('%H:%M:%S')}\n"))
        self.stdout.write(self.style.SUCCESS(f"🛑 Daily task finished at {datetime.now().strftime('%H:%M:%S')}\n"))
