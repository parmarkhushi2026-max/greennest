from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from store.models import CareReminder


class Command(BaseCommand):
    help = "Email due plant-care reminders and schedule each next reminder."

    def handle(self, *args, **options):
        due_reminders = CareReminder.objects.filter(
            active=True,
            next_reminder__lte=timezone.localdate(),
        ).select_related("user", "product")
        sent = 0
        skipped = 0
        for reminder in due_reminders:
            if not reminder.user.email:
                skipped += 1
                continue
            sent_count = send_mail(
                subject=f"Time to check on {reminder.plant_name}",
                message=(
                    f"Hi {reminder.user.first_name or reminder.user.username},\n\n"
                    f"This is your GreenNest reminder to check on {reminder.plant_name}. "
                    "Check the soil and give your plant the care it needs.\n\n"
                    "Happy growing,\nGreenNest"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reminder.user.email],
                fail_silently=False,
            )
            if sent_count != 1:
                raise CommandError(f"Could not send care reminder {reminder.pk}; its schedule was not advanced.")
            reminder.next_reminder = max(reminder.next_reminder, timezone.localdate()) + timedelta(
                days=reminder.interval_days
            )
            reminder.save(update_fields=["next_reminder"])
            sent += 1
        self.stdout.write(self.style.SUCCESS(
            f"Sent {sent} care reminder(s); skipped {skipped} without an email address."
        ))
