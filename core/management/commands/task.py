from datetime import datetime

from django.core.management.base import BaseCommand

from core import service


class Command(BaseCommand):
    help = 'Send DB backup email, then run event reminders until midnight'

    # ================================================================
    # ENTRY POINT
    # ================================================================

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"🚀 Daily command started at {datetime.now().strftime('%H:%M:%S')}\n"))

        service.sendDatabaseBackup()

        self.stdout.write(self.style.SUCCESS('🛑 Command finished, exiting.\n'))
