import firebase_admin
from firebase_admin import credentials, firestore
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
import json
import os
from django.views.decorators.csrf import csrf_exempt

from database.controllers.imageController import fetch_image_data

# Fetch Firebase credentials from environment variable
firebase_credentials_path = os.getenv('FIREBASE_ADMIN_CREDENTIALS')

# Debugging: Ensure the path is correctly retrieved
if not firebase_credentials_path:
    raise ValueError('FIREBASE_ADMIN_CREDENTIALS environment variable is not set.')

print('Firebase JSON Path:', firebase_credentials_path)

# Ensure Firebase is initialized only once
if not firebase_admin._apps:
    try:
        if os.path.exists(firebase_credentials_path):
            cred = credentials.Certificate(firebase_credentials_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Initialized Successfully")
        else:
            raise FileNotFoundError(f"Firebase credentials file not found at {firebase_credentials_path}")
    except Exception as e:
        print("Firebase Initialization Error:", str(e))
        raise

# Ensure Firestore is initialized
try:
    db = firestore.client()
    print("Firestore Initialized Successfully")
except Exception as e:
    print("Firestore Initialization Error:", str(e))
    raise

creds = service_account.Credentials.from_service_account_file(
    firebase_credentials_path, scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Ensure access token is acquired before making any requests to Firebase
def fetch_access_token():
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token

@csrf_exempt
def push_notifications(tokens: list, name, age, last_location_seen, last_date_time_seen, image, id):
    endpoint = f'https://fcm.googleapis.com/v1/projects/{os.getenv("FIREBASE_PROJECT_NAME")}/messages:send'
    
    # Enclose inside a for-loop as each token in the list is iterated
    for token in tokens:
        # Define message payload alongside the current token
        message = {
            'message': {
                'notification': {
                    'title': f'{name}, declared missing just now.',
                    'body': f'{name}, {age}, was last seen at {last_date_time_seen} in {last_location_seen}. Open the application to see more information about this person.',
                },
                'token': token,
                'android': {
                    'notification': {
                        'image': fetch_image_data(image),
                    }
                },
                'apns': {
                    'payload': {
                        'aps': {
                            'mutable-content': 1
                        }
                    },
                    'fcm_options': {
                        'image': fetch_image_data(image)
                    }
                }
            }
        }

        # Define JSON payload header as Application/JSON including Bearer token fetched from Firebase Credentials
        headers = {
            'Authorization': f'Bearer {fetch_access_token()}',
            'Content-Type': 'application/json; UTF-8',
        }

        # Send request to FCM for each token
        response = requests.post(endpoint, headers=headers, data=json.dumps(message))

        if response.status_code == 200:
            print(f'Successfully sent notification to {token}')
        else:
            print(f'Unable to send notification to {token}: {response.status_code}, {response.text}')

# Fetch available FCM tokens from Firebase, both Android and iOS
def get_fcm_tokens():
    # Get snapshot of the collection from Firebase
    tokens_snapshot = db.collection('fcmTokens').stream()
    fcm_tokens = [doc.to_dict().get('token') for doc in tokens_snapshot if doc.to_dict().get('token')]
    
    # Trigger if no tokens exist
    if not fcm_tokens:
        print('No FCM tokens found in Firestore.')
    
    unique_tokens = list(set(fcm_tokens))  # Ensure there are no duplicate tokens coming in from Firebase
    print(f"Retrieved {len(unique_tokens)} unique FCM tokens")
    
    return unique_tokens