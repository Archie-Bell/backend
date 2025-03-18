import os
import uuid
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from pymongo import MongoClient
import datetime
# Connect to MongoDB using Django settings
client = MongoClient(settings.MONGO_DB_URI)  
db = client[settings.MONGO_DB_NAME]  # Database Name: ArchieBell
collection = db[settings.MISSING_PERSONS_COLLECTION]  # Collection: MissingPersonsList
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
 
        # Validate required fields
        if not all([name, age, last_location_seen, last_date_time_seen, image]):
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
        image_url = f"/api/uploads/{unique_filename}"  # Public URL path
        new_record = {
            "name": name,
            "age": age,
            "last_location_seen": last_location_seen,
            "last_date_time_seen": last_date_time_seen,
            "additional_info": additional_info,
            "image_url": image_url , 
             "form_status": "Pending",  # Default status
             "submission_date": datetime.datetime.utcnow(),  # Current UTC time
             "last_updated_date": datetime.datetime.utcnow(),  # Initially the same as submission date
             "updated_by": None  # Updated by will be set when an admin modifies the record
        }
    # Insert into MongoDB
        result = collection.insert_one(new_record)
        print(f"Inserted ID: {result.inserted_id}")  # Debugging

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

    return JsonResponse(_data, safe=False, json_dumps_params={'indent': 4})
    

