import os
import uuid
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from pymongo import MongoClient
import datetime

from database.controllers.notificationController import push_notifications, get_fcm_tokens
# Connect to MongoDB using Django settings
client = MongoClient(settings.MONGO_DB_URI)  
db = client[settings.MONGO_DB_NAME]
collection = db[settings.MISSING_PERSONS_COLLECTION]
ALLOWED_IMAGE_TYPES = ['jpg', 'jpeg', 'png']
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def submit_form(request):
    try:
        # Extract form data
        data = request.data  
        image = request.FILES['image']
        name = data.get('name')
        age = data.get('age')
        last_location_seen = data.get('last_location_seen')
        last_date_time_seen = data.get('last_date_time_seen')
        additional_info = data.get('additional_info')
        image_url = data.get("image_url")  
        reporter_legal_name = data.get('reporter_legal_name')
        reporter_phone_number = data.get('reporter_phone_number')
 
        # Validate required fields
        if not all([name, age, last_location_seen, last_date_time_seen, image,reporter_legal_name, reporter_phone_number]):
            return JsonResponse({'error': 'All fields are required'}, status=400)

        # Save image
        unique_filename = f"{uuid.uuid4().hex}.png"
        output_dir = os.path.join('database', 'uploads')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, unique_filename)

        with open(output_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)

        # Save record in database
        image_url = f"/uploads/{unique_filename}"  # Public URL path
        new_record = {
            "name": name,
            "age": int(age),
            "last_location_seen": last_location_seen,
            "last_date_time_seen": last_date_time_seen,
            "additional_info": additional_info,
            "image_url": image_url, 
            "form_status": "Pending",  # Default status
            "submission_date": datetime.datetime.utcnow(),  # Current UTC time
            "last_updated_date": datetime.datetime.utcnow(),  # Initially the same as submission date
            "reporter_legal_name": reporter_legal_name,
            "reporter_phone_number": reporter_phone_number,
            "updated_by": None  # Updated by will be set when an admin modifies the record
        }
    # Insert into MongoDB
        result = collection.insert_one(new_record)
        print(f"Inserted ID: {result.inserted_id}")  # Debugging
        
        tokens = get_fcm_tokens()  # Fetch currently available FCM tokens stored inside Firebase
        
        push_notifications(tokens, name, age, last_location_seen, last_date_time_seen)

        return JsonResponse({'message': 'Form submitted successfully', 'image_url': image_url}, status=200)

    except Exception as e:
        return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)


# Get all records inside the collection (MissingPersonsList)
@api_view(['GET'])
def get_missing_persons(request):
    # API to fetch all missing persons.
    _data = list(collection.find({}))
    for data in _data:
        data['_id'] = str(data['_id'])  
        data['submission_date'] = data.get('submission_date', None)  
        data['last_updated_date'] = data.get('last_updated_date', None)
        data['form_status'] = data.get('form_status', "Pending")
        data['updated_by'] = data.get('updated_by', None)
        data['reporter_legal_name'] = data.get('reporter_legal_name', None)  
        data['reporter_phone_number'] = data.get('reporter_phone_number', None)  
        data['rejection_reason'] = data.get('rejection_reason', None)  

    return JsonResponse(_data, safe=False, json_dumps_params={'indent': 4})

# [DEBUG] delete existing data inside MissingPersonsList
@api_view(['DELETE'])
def delete_collection_data(request):
    try:
        result = collection.delete_many({})
        
        if result.deleted_count > 0:
            return JsonResponse(
                {"message": f"Successfully deleted {result.deleted_count} records."},
                status=200
            )
        else:
            return JsonResponse(
                {"message": "No records to delete."},
                status=404
            )
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )