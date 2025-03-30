import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from database.controllers.authController import verify_auth
from datetime import datetime
import jwt

from database.controllers.notificationController import get_fcm_tokens, push_notifications  

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_DB_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

@csrf_exempt
@verify_auth
def update_submission(request, **kwargs):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            submission_id = data.get("submission_id")
            status = data.get("status")
            rejection_reason = data.get("rejection_reason", None) 
            
            # Extract staff email from the authenticated user
            auth_header = request.headers.get("Authorization")
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            updated_by_email = payload.get("email")

            # Find submission table (MissingPersonsList)
            submission = db["PendingSubmissionList"].find_one({"_id": ObjectId(submission_id)})
            if not submission:
                return JsonResponse({"error": "Submission not found"}, status=404)

            name = submission.get('name')
            age = submission.get('age')
            last_location_seen = submission.get('last_location_seen')
            last_date_time_seen = submission.get('last_date_time_seen')
            
            # Update status, last_updated_date, and updated_by
            update_data = {
                "$set": {
                    "form_status": status,
                    "last_updated_date": datetime.utcnow(),  # Update timestamp
                    "updated_by": updated_by_email,  # Store the email of the staff updating it
                }
            }
            
            if status == "Approved":
                # Add the updated submission data to the MissingPersonsList
                missing_person_data = {
                    'name': name,
                    'age': age,
                    'last_location_seen': last_location_seen,
                    'last_date_time_seen': last_date_time_seen,
                    'image_url': submission.get('image_url'),
                    'form_status': status,
                    'submission_date': submission.get('submission_date'),
                    'last_updated_date': datetime.utcnow(),
                    'reporter_legal_name': submission.get('reporter_legal_name'),
                    'reporter_phone_number': submission.get('reporter_phone_number'),
                    'updated_by': updated_by_email,
                }

                # Insert the data into the MissingPersonsList collection
                db["MissingPersonsList"].insert_one(missing_person_data)
                print(f'Successfully approved and added to MissingPersonsList: {submission_id}.')

                tokens = get_fcm_tokens()  # Fetch currently available FCM tokens stored inside Firebase
                push_notifications(tokens, name, age, last_location_seen, last_date_time_seen, submission_id)

                # Delete the submission from pending list as it's no longer required
                db["PendingSubmissionList"].delete_one({"_id": ObjectId(submission_id)})
                print(f'Successfully deleted {submission_id} from pending list.')
                
            elif status == "Rejected":
                # If form status is rejected, exclude images and add to the rejected list
                db["RejectedSubmissionList"].insert_one({
                    '_id': ObjectId(submission_id),
                    'reported_missing_person': submission.get('name'),
                    'reported_missing_location': submission.get('last_location_seen'),
                    'reported_date_time_missing': submission.get('last_date_time_seen'),
                    'reporter_legal_name': submission.get('reporter_legal_name'),
                    'reporter_phone_number': submission.get('reporter_phone_number'),
                    'form_status': status,
                    'rejection_reason': rejection_reason,
                    'last_updated_date': datetime.utcnow(),
                    'submission_date': submission.get('submission_date'),
                    'updated_by': updated_by_email
                })
                print(f'Successfully rejected submission {submission_id}.')
                
                db["PendingSubmissionList"].delete_one({'_id': ObjectId(submission_id)})
                print(f'Successfully deleted {submission_id} from pending list.')

            # Otherwise, update the document in the original collection
            db["PendingSubmissionList"].update_one({"_id": ObjectId(submission_id)}, update_data)

            return JsonResponse({"message": f"Submission {status}"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)