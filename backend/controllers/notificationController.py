import firebase_admin
from firebase_admin import credentials, messaging, firestore
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_CREDENTIALS'))
    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

@csrf_exempt
def push_notifications(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get('name')
            age = data.get('age')
            id = data.get('id')
            last_location_seen = data.get('lastLocationSeen')
            last_date_time_seen = data.get('lastDateTimeSeen')
            additional_info = data.get('additionalInfo')

            # Fetch FCM tokens from Firestore
            tokens_snapshot = db.collection('fcmTokens').stream()
            fcm_tokens = [doc.to_dict().get('token') for doc in tokens_snapshot if doc.to_dict().get('token')]

            if not fcm_tokens:
                return JsonResponse({'message': 'No FCM tokens found in the database.'}, status=400)

            # Ensure each token is unique
            unique_tokens = list(set(fcm_tokens))

            if not unique_tokens:
                return JsonResponse({'message': 'No valid FCM tokens available.'}, status=400)

            # Define notification message
            message = messaging.MulticastMessage(
                tokens=unique_tokens,
                notification=messaging.Notification(
                    title="Missing Person Alert",
                    body=f"{name}, aged {age}, has been reported missing just now, press this notification for more details."
                ),
                data={
                    'id': str(id),
                    'name': name,
                    'age': str(age),
                    'lastLocationSeen': last_location_seen,
                    'lastDateTimeSeen': last_date_time_seen,
                    'additionalInfo': additional_info,
                }
            )

            # Send notifications
            response = messaging.send_multicast(message)

            # Check for failed tokens
            failed_tokens = [
                unique_tokens[i]
                for i, resp in enumerate(response.responses) if not resp.success
            ]

            if failed_tokens:
                return JsonResponse({'message': 'Notifications failed to push on some devices', 'failedTokens': failed_tokens}, status=500)

            return JsonResponse({'message': 'Notification successfully pushed to all devices'}, status=200)

        except Exception as e:
            return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)

    return JsonResponse({'message': 'Invalid request method'}, status=405)
