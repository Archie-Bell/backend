import base64
import glob
import io
import os
import uuid
from django.conf import settings
from django.http import FileResponse, HttpResponse, HttpResponseNotFound, JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from pymongo import MongoClient
from bson import ObjectId
from PIL import Image
import datetime

from database.controllers.authController import verify_auth
from database.controllers.notificationController import push_notifications, get_fcm_tokens
# Connect to MongoDB using Django settings
client = MongoClient(settings.MONGO_DB_URI)  
db = client[settings.MONGO_DB_NAME]
missing_persons_collection = db[settings.MISSING_PERSONS_COLLECTION]
pending_list_collection = db[settings.PENDING_SUBMISSION_COLLECTION]
rejected_list_collection = db[settings.REJECTED_SUBMISSION_COLLECTION]
ALLOWED_IMAGE_TYPES = ['jpg', 'jpeg', 'png']
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

# This is the function where you handle image saving and processing
def save_image(base64_image):
    try:
        # Decode the base64 image data
        image_data = base64.b64decode(base64_image)
        
        # Open the image using PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Get the dimensions of the image
        width, height = image.size
        
        # Calculate the new crop box for 1:1 aspect ratio (crop the smallest dimension)
        new_dimension = min(width, height)
        left = (width - new_dimension) // 2
        top = (height - new_dimension) // 2
        right = (width + new_dimension) // 2
        bottom = (height + new_dimension) // 2
        
        # Crop the image to 1:1 aspect ratio
        image = image.crop((left, top, right, bottom))
        
        # Resize the image to 400x400
        image = image.resize((400, 400))
        
        # Generate a unique filename for the image
        unique_filename = f"{uuid.uuid4().hex}.png"
        output_dir = os.path.join('database', 'uploads')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, unique_filename)
        
        # Save the processed image to the output path
        image.save(output_path, format="PNG")
        
        # Return the image URL for reference in the database
        image_url = f"/api/uploads/{unique_filename}"
        return image_url, output_path
    
    except Exception as e:
        raise Exception(f"Error processing the image: {str(e)}")

# In your submit_form function, you can now call save_image
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def submit_form(request):
    try:
        print('attempting to submit form')
        # Extract form data
        data = request.data  
        base64_image = data.get('image')
        name = data.get('name')
        age = data.get('age')
        last_location_seen = data.get('last_location_seen')
        last_date_time_seen = data.get('last_date_time_seen')
        additional_info = data.get('additional_info')
        reporter_legal_name = data.get('reporter_legal_name')
        reporter_phone_number = data.get('reporter_phone_number')
        
        if base64_image.startswith('data:image'):
            base64_image = base64_image.split(',')[1]
            
        if not additional_info:
            additional_info = 'No description was provided.'
        
        # Validate required fields
        if not all([name, age, last_location_seen, last_date_time_seen, base64_image, reporter_legal_name, reporter_phone_number]):
            return JsonResponse({'error': 'All fields are required'}, status=400)

        # Process and save the image, return the image URL
        image_url, output_path = save_image(base64_image)
                
        # Format the last seen date
        str_to_date = datetime.datetime.strptime(last_date_time_seen, "%Y-%m-%dT%H:%M")
        formatted_date = str_to_date.strftime("%d %b. %Y, %I:%M %p")
        
        # Save record in database
        new_record = {
            "name": name,
            "age": int(age),
            "last_location_seen": last_location_seen,
            "last_date_time_seen": formatted_date,
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
        result = pending_list_collection.insert_one(new_record)

        return JsonResponse({'message': 'Form submitted successfully', 'image_url': image_url}, status=200)

    except Exception as e:
        return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)

# Get all records inside the collection (PendingSubmissionList)
@api_view(['GET'])
@verify_auth
def fetch_pending_list(request, staff_email=None):
    # API to fetch all missing persons in pending list.
    _data = list(pending_list_collection.find({}))
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

# Get all records inside the collection (MissingPersonsList)
@api_view(['GET'])
def fetch_missing_person_list(request):
    # API to fetch all missing persons in the main list.
    _data = list(missing_persons_collection.find({}))
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

# Implement singular data fetching for pending person
@api_view(['GET'])
@verify_auth
def fetch_pending_person(request, person_id=None, staff_email=None):
    if person_id is None:
        return JsonResponse({"error": "No person id provided."}, status=400)
    
    try:
        # Convert the string id to ObjectId
        person_object_id = ObjectId(person_id)
    except Exception as e:
        return JsonResponse({"error": f"Invalid ID format: {str(e)}"}, status=400)
    
    # Fetch the missing person based on the ID
    person = pending_list_collection.find_one({"_id": person_object_id})

    if person is None:
        return JsonResponse({"error": "Person not found."}, status=404)
    
    # Ensure the person data is formatted correctly before returning it
    person['_id'] = str(person['_id'])  # Convert ObjectId to string
    person['submission_date'] = person.get('submission_date', None)
    person['last_updated_date'] = person.get('last_updated_date', None)
    person['form_status'] = person.get('form_status', "Pending")
    person['updated_by'] = person.get('updated_by', None)
    person['reporter_legal_name'] = person.get('reporter_legal_name', None)
    person['reporter_phone_number'] = person.get('reporter_phone_number', None)
    person['rejection_reason'] = person.get('rejection_reason', None)

    return JsonResponse(person, safe=False, json_dumps_params={'indent': 4})

# Implement singular data fetching for missing person
@api_view(['GET'])
def fetch_missing_person(request, person_id=None):
    if person_id is None:
        return JsonResponse({"error": "No person id provided."}, status=400)
    
    try:
        # Convert the string id to ObjectId
        person_object_id = ObjectId(person_id)
    except Exception as e:
        return JsonResponse({"error": f"Invalid ID format: {str(e)}"}, status=400)
    
    # Fetch the missing person based on the ID
    person = missing_persons_collection.find_one({"_id": person_object_id})

    if person is None:
        return JsonResponse({"error": "Person not found."}, status=404)
    
    # Ensure the person data is formatted correctly before returning it
    person['_id'] = str(person['_id'])  # Convert ObjectId to string
    person['submission_date'] = person.get('submission_date', None)
    person['last_updated_date'] = person.get('last_updated_date', None)
    person['form_status'] = person.get('form_status', "Pending")
    person['updated_by'] = person.get('updated_by', None)
    person['reporter_legal_name'] = person.get('reporter_legal_name', None)
    person['reporter_phone_number'] = person.get('reporter_phone_number', None)
    person['additional_info'] = person.get('additional_info')

    return JsonResponse(person, safe=False, json_dumps_params={'indent': 4})

# [DEBUG] delete existing data inside MissingPersonsList
@api_view(['DELETE'])
def delete_collection_data(request):
    try:
        file_list = glob.glob(f'{os.path.join('database', 'uploads')}/*.png' or f'{os.path.join('database', 'uploads')}/*.jpg' or f'{os.path.join('database', 'uploads')}/*.jpeg', recursive=True)
        result = missing_persons_collection.delete_many({}) and pending_list_collection.delete_many({}) and rejected_list_collection.delete_many({})
        
        for file in file_list:
            try:
                os.remove(file)
            except OSError:
                return JsonResponse(
                    {"error": str(e)},
                    status=500
                )
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