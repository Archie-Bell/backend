import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from database.controllers.authController import verify_auth
from datetime import datetime, timezone
import jwt

from rest_framework.decorators import api_view, parser_classes

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
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
            additional_info = submission.get('additional_info')
            image_url = submission.get('image_url')
            
            image_url = image_url.split('/api/uploads/')[1]
            
            # Update status, last_updated_date, and updated_by
            update_data = {
                "$set": {
                    "form_status": status,
                    "last_updated_date": datetime.now(timezone.utc),  # Update timestamp
                    "updated_by": updated_by_email,  # Store the email of the staff updating it
                }
            }
            
            if status == "Approved":
                # Add the updated submission data to the MissingPersonsList
                missing_person_data = {
                    '_id': ObjectId(submission_id),
                    'name': name,
                    'age': age,
                    'last_location_seen': last_location_seen,
                    'last_date_time_seen': last_date_time_seen,
                    'additional_info': additional_info,
                    'image_url': submission.get('image_url'),
                    'form_status': status,
                    'submission_date': submission.get('submission_date'),
                    'last_updated_date': datetime.now(timezone.utc),
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
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "updates",
                    {
                        "type": "submission_update",
                        "message": f"Successfully approved submission ID: {submission_id}",
                    }
                )
                
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
                    'last_updated_date': datetime.now(timezone.utc),
                    'submission_date': submission.get('submission_date'),
                    'updated_by': updated_by_email
                })
                print(f'Successfully rejected submission {submission_id}.')
                
                db["PendingSubmissionList"].delete_one({'_id': ObjectId(submission_id)})
                print(f'Successfully deleted {submission_id} from pending list.')
                
                file = os.path.join('database', 'uploads', image_url)
                os.remove(file)
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "updates",
                    {
                        "type": "submission_update",
                        "message": f"Successfully rejected submission ID: {submission_id}",
                    }
                )

            # Otherwise, update the document in the original collection
            db["PendingSubmissionList"].update_one({"_id": ObjectId(submission_id)}, update_data)

            return JsonResponse({"message": f"Submission {status}"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=405)

@verify_auth
@api_view(['POST'])
def handle_active_search_submission(request, **kwargs):
    try:
        data = request.data
        submission_id = data.get('submission_id')
        parent_id = data.get('parent_id')
        reported_location = data.get('reported_location')
        reported_datetime = data.get('reported_datetime')
        reported_information = data.get('reported_information')
        submission_status = data.get('submission_status')
        rejection_reason = data.get('rejection_reason')
        submission_date = data.get('submission_date')
        image_url = data.get('image_url')
        image_url = image_url.split('/api/uploads/submissions/')[1]
        print(image_url)
        
        if submission_status == 'approved':
            print('Submission approved, proceeding with data deletion process.')
            db['MissingPersonsList'].delete_many({ '_id': ObjectId(parent_id) })
            db['FoundSubmissionList'].delete_many({ '_parent_id': ObjectId(parent_id) })
            db['RejectedFoundSubmissionList'].delete_many({ '_parent_id': ObjectId(parent_id) })
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "active_search",
                {
                    "type": "active_search_message",
                    "message": f"Approved found submission for parent: {parent_id}",
                }
            )
            
        if submission_status == 'rejected':
            print('Submission rejected, adding record for assessment.')
            db['RejectedFoundSubmissionList'].insert_one({
                '_id': ObjectId(submission_id),
                '_parent_id': ObjectId(parent_id),
                'reported_location': reported_location,
                'reported_datetime': reported_datetime,
                'reported_information': reported_information,
                'submission_status': 'Rejected',
                'rejection_reason': rejection_reason,
                'submission_date': submission_date,
                'last_updated_date': datetime.now(timezone.utc),
                'updated_by': kwargs.get('staff_email')
            })
            
            db['FoundSubmissionList'].find_one_and_delete({ '_id': ObjectId(submission_id) })
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "active_search",
                {
                    "type": "active_search_message",
                    "message": f"Declined found submission for parent: {parent_id}",
                }
            )
        
        file = os.path.join('database', 'uploads', 'submissions', image_url)
        print(f'file {file}')
        os.remove(file)

        return JsonResponse({ 'message': 'Process finished' }, status=200)
    except Exception as e:
        return JsonResponse({ 'error': f'Something went wrong: {str(e)}' }, status=500)