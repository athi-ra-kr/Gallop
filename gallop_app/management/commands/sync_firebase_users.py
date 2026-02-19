from django.core.management.base import BaseCommand
from gallop_app.models import StudentProfile
from gallop_app.firebase_helper import get_firebase_users
from datetime import datetime
from django.utils import timezone


def parse_firebase_date(date_string):
    """
    Convert Firebase date like 'Jan 30, 2026' → timezone aware datetime
    """
    if not date_string or date_string == "N/A":
        return None

    try:
        naive_date = datetime.strptime(date_string, "%b %d, %Y")
        return timezone.make_aware(naive_date)
    except:
        return None


class Command(BaseCommand):
    help = "Sync Firebase users into Django DB"

    def handle(self, *args, **kwargs):
        firebase_users = get_firebase_users()

        for u in firebase_users:
            StudentProfile.objects.update_or_create(
                firebase_uid=u.get("uid"),
                defaults={
                    "email": u.get("email"),
                    "provider": u.get("provider"),
                    "created_at": parse_firebase_date(u.get("created")),
                    "last_login_time": parse_firebase_date(u.get("signed_in")),
                },
            )

        self.stdout.write(self.style.SUCCESS("Firebase users synced successfully"))