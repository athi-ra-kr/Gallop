import firebase_admin
from firebase_admin import credentials, auth
from datetime import datetime
import os

import os
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings

# This creates the correct path to the file inside gallop_app
cred_path = os.path.join(settings.BASE_DIR, 'gallop_app', 'firebase-key.json')

def get_firebase_users():
    if not firebase_admin._apps:
        # Use the new cred_path variable here
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    firebase_data = []
    # 2. Fetch all users from Firebase
    page = auth.list_users()
    
    for user in page.users:
        # Convert timestamp to readable format
        created_at = datetime.fromtimestamp(user.user_metadata.creation_timestamp / 1000).strftime('%b %d, %Y')
        
        last_login = user.user_metadata.last_sign_in_timestamp
        signed_in = datetime.fromtimestamp(last_login / 1000).strftime('%b %d, %Y') if last_login else "Never"

        # Determine the provider (Google or Email)
        provider = "Google" if "google.com" in [p.provider_id for p in user.provider_data] else "Email"

        firebase_data.append({
            'email': user.email,
            'provider': provider,
            'created': created_at,
            'signed_in': signed_in,
            'uid': user.uid
        })
    
    return firebase_data