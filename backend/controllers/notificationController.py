import firebase_admin
from firebase_admin import credentials, messaging, firestore
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os

# Fetch Firebase credentials from environment variable
firebase_credentials_path = os.getenv('FIREBASE_ADMIN_CREDENTIALS')

# Debugging: Ensure the path is correctly retrieved
if not firebase_credentials_path:
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS environment variable is not set.")

print("Firebase JSON Path:", firebase_credentials_path)

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

@csrf_exempt
def push_notifications(request):
    if request.method != "POST":
        return JsonResponse({'message': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        required_fields = ['name', 'age', 'id', 'lastLocationSeen', 'lastDateTimeSeen', 'additionalInfo']
        
        if not all(field in data for field in required_fields):
            return JsonResponse({'message': 'Missing required fields'}, status=400)
        
        name = data['name']
        age = data['age']
        id = data['id']
        last_location_seen = data['lastLocationSeen']
        last_date_time_seen = data['lastDateTimeSeen']
        additional_info = data['additionalInfo']
        
        # Fetch FCM tokens from Firestore
        tokens_snapshot = db.collection('fcmTokens').stream()
        fcm_tokens = [doc.to_dict().get('token') for doc in tokens_snapshot if doc.to_dict().get('token')]

        if not fcm_tokens:
            return JsonResponse({'message': 'No FCM tokens found in Firestore.'}, status=400)

        # Ensure each token is unique
        unique_tokens = list(set(fcm_tokens))
        print(f"Retrieved {len(unique_tokens)} unique FCM tokens")

        if not unique_tokens:
            return JsonResponse({'message': 'No valid FCM tokens available.'}, status=400)

        # Define notification message
        message = messaging.MulticastMessage(
            tokens=unique_tokens,
            notification=messaging.Notification(
                title="Missing Person Alert",
                body=f"{name}, aged {age}, has been reported missing just now. Press this notification for more details."
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
        failed_tokens = [unique_tokens[i] for i, resp in enumerate(response.responses) if not resp.success]

        if failed_tokens:
            print("Some notifications failed to send:", failed_tokens)
            return JsonResponse({'message': 'Some notifications failed', 'failedTokens': failed_tokens}, status=500)

        print("Notification sent successfully")
        return JsonResponse({'message': 'Notification sent successfully'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON format'}, status=400)
    except Exception as e:
        print("Error sending notification:", str(e))
        return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)