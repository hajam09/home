import os
import time
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import EventReminder

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------

LOOP_SLEEP_SECONDS = 60 * 5  # 5 minutes
MAX_EMAILS_PER_DAY = 20
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60 * 2  # 2 minutes


class Command(BaseCommand):
    help = 'Send DB backup email, then run event reminders until midnight'

    # ================================================================
    # ENTRY POINT
    # ================================================================

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"🚀 Daily command started at {datetime.now().strftime('%H:%M:%S')}\n"))

        self.sendDatabaseBackup()
        # self.runReminderLoopUntilMidnight()

        self.stdout.write(self.style.SUCCESS("🛑 Command finished, exiting.\n"))

    # ================================================================
    # DATABASE BACKUP EMAIL
    # ================================================================

    def sendDatabaseBackup(self):
        databasePath = os.path.join(settings.BASE_DIR, 'db.sqlite3')

        if not os.path.exists(databasePath):
            self.stderr.write(self.style.ERROR(f'❌ DB file not found: {databasePath}'))
            return

        email = EmailMessage(
            subject=f"BarkingHome DB Backup - {datetime.now().strftime('%Y-%m-%d')}",
            body="Attached is the current db.sqlite3 file.",
            from_email=settings.EMAIL_HOST_USER,
            to=['qmwebprog2019@gmail.com'],
        )

        with open(databasePath, 'rb') as f:
            email.attach('db.sqlite3', f.read(), 'application/octet-stream')

        try:
            email.send()
            self.stdout.write(
                self.style.SUCCESS(
                    f"📧 DB backup sent at {datetime.now().strftime('%H:%M:%S')}\n"
                )
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ DB backup failed: {e}\n"))

    def convertSeconds(self, seconds: int) -> str:
        units = [
            ("year", 365 * 24 * 60 * 60),
            ("month", 30 * 24 * 60 * 60),
            ("week", 7 * 24 * 60 * 60),
            ("day", 24 * 60 * 60),
            ("hour", 60 * 60),
            ("minute", 60),
            ("second", 1),
        ]

        result = []

        for name, unitSeconds in units:
            value, seconds = divmod(seconds, unitSeconds)
            if value:
                result.append(f"{value} {name}{'s' if value != 1 else ''}")

        return ", ".join(result) if result else "0 seconds"

    # ================================================================
    # REMINDER LOOP (UNTIL MIDNIGHT)
    # ================================================================

    def runReminderLoopUntilMidnight(self):
        now = timezone.now()
        midnight = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        self.stdout.write(
            self.style.NOTICE(
                f"⏰ Running reminders until {midnight.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        )

        while timezone.now() < midnight:
            loopNow = timezone.now()
            self.stdout.write(
                f"🕒 [{loopNow.strftime('%H:%M:%S')}] Checking reminders..."
            )

            reminders = EventReminder.objects.filter(
                completed=False
            ).order_by('eventDateTime')

            for reminder in reminders:
                self.processReminder(reminder, loopNow)

            remainingSeconds = int((midnight - timezone.now()).total_seconds())
            sleepSeconds = min(LOOP_SLEEP_SECONDS, max(0, remainingSeconds))

            if sleepSeconds <= 0:
                break

            self.stdout.write(f"🔁 Sleeping for {self.convertSeconds(sleepSeconds)}...\n")
            time.sleep(sleepSeconds)

    # ================================================================
    # PROCESS SINGLE REMINDER
    # ================================================================

    def processReminder(self, reminder: EventReminder, now):
        # 1️⃣ Event reached → mark completed
        if now >= reminder.eventDateTime:
            reminder.completed = True
            reminder.save(update_fields=['completed'])
            self.stdout.write(
                self.style.SUCCESS(f"✅ Completed: {reminder.title}")
            )
            return

        # 2️⃣ Auto-fix nextReminderDateTime
        if not reminder.nextReminderDateTime:
            reminder.nextReminderDateTime = max(now, reminder.getStartDateTime())
            reminder.save(update_fields=['nextReminderDateTime'])
            self.stdout.write(
                self.style.WARNING(
                    f"🛠 Auto-fixed nextReminderDateTime for {reminder.title}"
                )
            )
            return

        if reminder.nextReminderDateTime > now:
            return

        # 3️⃣ Reset daily counters
        today = now.date()
        if reminder.lastSentDate != today:
            reminder.lastSentDate = today
            reminder.sentCountToday = 0
            reminder.retryCount = 0

        # 4️⃣ Daily safety cap
        if reminder.sentCountToday >= MAX_EMAILS_PER_DAY:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️ Daily email limit reached for {reminder.title}"
                )
            )
            return

        # 5️⃣ Try sending email
        email = EmailMessage(
            subject=f"Reminder: {reminder.title}",
            body=reminder.message or "",
            from_email=settings.EMAIL_HOST_USER,
            to=reminder.getEmailList(),
        )

        try:
            email.send()

        except Exception as e:
            reminder.retryCount += 1
            reminder.lastFailureDateTime = now

            if reminder.retryCount <= MAX_RETRIES:
                reminder.nextReminderDateTime = now + timedelta(seconds=RETRY_DELAY_SECONDS)
                self.stdout.write(
                    self.style.WARNING(
                        f"🔁 Retry {reminder.retryCount}/{MAX_RETRIES} "
                        f"scheduled for {reminder.title}: {e}"
                    )
                )
            else:
                reminder.retryCount = 0
                reminder.nextReminderDateTime = now + reminder.getIntervalDelta()
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Max retries reached for {reminder.title}, "
                        f"skipping until next interval"
                    )
                )

            reminder.save(
                update_fields=[
                    'retryCount',
                    'lastFailureDateTime',
                    'nextReminderDateTime',
                ]
            )
            return

        # 6️⃣ Success → update state
        reminder.retryCount = 0
        reminder.sentCountToday += 1
        reminder.lastSentDate = today
        reminder.nextReminderDateTime = now + reminder.getIntervalDelta()

        reminder.save(
            update_fields=[
                'retryCount',
                'sentCountToday',
                'lastSentDate',
                'nextReminderDateTime',
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"📧 Sent reminder ({reminder.sentCountToday}/{MAX_EMAILS_PER_DAY}) "
                f"for {reminder.title}"
            )
        )
