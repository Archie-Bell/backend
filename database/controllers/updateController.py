import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from database.controllers.authController import staff_required
from datetime import datetime
import jwt  


# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_DB_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

@csrf_exempt
@staff_required
def update_submission(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            submission_id = data.get("submission_id")
            status = data.get("status")

            # Extract staff email from the authenticated user
            auth_header = request.headers.get("Authorization")
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            updated_by_email = payload.get("email")

            # Find submission table (MissingPersonsList)
            submission = db["MissingPersonsList"].find_one({"_id": ObjectId(submission_id)})
            if not submission:
                return JsonResponse({"error": "Submission not found"}, status=404)

            # Update status, last_updated_date, and updated_by
            update_data = {
                "$set": {
                    "form_status": status,
                    "last_updated_date": datetime.utcnow(),  # Update timestamp
                    "updated_by": updated_by_email,  # Store the email of the staff updating it
                }
            }
            db["MissingPersonsList"].update_one({"_id": ObjectId(submission_id)}, update_data)

            return JsonResponse({"message": f"Submission {status}"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)