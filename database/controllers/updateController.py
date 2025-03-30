import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from database.controllers.authController import staff_required, verify_auth
from datetime import datetime
import jwt

from database.controllers.formController import fetch_image_data
from database.controllers.notificationController import get_fcm_tokens, push_notifications  

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_DB_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

@csrf_exempt
@verify_auth
def update_submission(request):
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
            image_url = submission.get('image_url').split('/api/uploads')
            print(image_url)
            
            # Update status, last_updated_date, and updated_by
            update_data = {
                "$set": {
                    "form_status": status,
                    "last_updated_date": datetime.utcnow(),  # Update timestamp
                    "updated_by": updated_by_email,  # Store the email of the staff updating it
                }
            }
            
            if status == "Approved":
                tokens = get_fcm_tokens()  # Fetch currently available FCM tokens stored inside Firebase
        
                push_notifications(tokens, name, age, last_location_seen, last_date_time_seen, fetch_image_data(image_url), submission_id)

            # If rejected, add rejection reason
            if status == "Rejected" and rejection_reason:
                update_data["$set"]["rejection_reason"] = rejection_reason

            # Move document to another collection if needed
            if status in ["Approved"]:  # You can define other conditions to move the document
                # 1. Insert the document into the target collection (e.g., 'ApprovedOrRejectedSubmissionList')
                db["MissingPersonsList"].insert_one(submission)

                # 2. Delete the document from the original collection (e.g., 'PendingSubmissionList')
                db["PendingSubmissionList"].delete_one({"_id": ObjectId(submission_id)})

            # Otherwise, update the document in the original collection
            db["PendingSubmissionList"].update_one({"_id": ObjectId(submission_id)}, update_data)

            return JsonResponse({"message": f"Submission {status}"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)
