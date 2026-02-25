import firebase_admin
from firebase_admin import credentials, auth
from datetime import datetime
import os
from django.conf import settings
from .models import StudentProfile   # ✅ ADD THIS

cred_path = os.path.join(settings.BASE_DIR, 'gallop_app', 'firebase-key.json')


def get_firebase_users():
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

    firebase_data = []

    page = auth.list_users()

    for user in page.users:

        created_at = datetime.fromtimestamp(
            user.user_metadata.creation_timestamp / 1000
        )

        last_login_ts = user.user_metadata.last_sign_in_timestamp
        last_login = (
            datetime.fromtimestamp(last_login_ts / 1000)
            if last_login_ts
            else None
        )

        provider = (
            "Google"
            if "google.com" in [p.provider_id for p in user.provider_data]
            else "Email"
        )

        email = user.email
        uid = user.uid

        firebase_data.append({
            'email': email,
            'provider': provider,
            'created': created_at.strftime('%b %d, %Y'),
            'signed_in': last_login.strftime('%b %d, %Y') if last_login else "Never",
            'uid': uid
        })

        # ✅ AUTO CREATE / UPDATE IN DJANGO DB
        if email:
            student, created = StudentProfile.objects.get_or_create(
                email=email,
                defaults={
                    "firebase_uid": uid,
                    "provider": provider,
                    "created_at": created_at,
                    "last_login_time": last_login,
                }
            )

            # 🔄 update existing records
            student.firebase_uid = uid
            student.provider = provider
            student.created_at = created_at
            student.last_login_time = last_login
            student.save()

    return firebase_data