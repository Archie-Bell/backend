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

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from database.controllers.authController import verify_auth

# Connect to MongoDB using Django settings
client = MongoClient(settings.MONGO_DB_URI)  
db = client[settings.MONGO_DB_NAME]
missing_persons_collection = db[settings.MISSING_PERSONS_COLLECTION]
pending_list_collection = db[settings.PENDING_SUBMISSION_COLLECTION]
rejected_list_collection = db[settings.REJECTED_SUBMISSION_COLLECTION]
found_submission_collection = db[settings.FOUND_SUBMISSION_COLLECTION]
rejected_found_submission_collection = db[settings.REJECTED_FOUND_SUBMISSION_COLLECTION]
ALLOWED_IMAGE_TYPES = ['jpg', 'jpeg', 'png']
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

def save_image(base64_image, submission_type):
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
        
        # Determine the output directory based on submission_type
        if submission_type == 0:
            output_dir = os.path.join('database', 'uploads')
            image_url = f"/api/uploads/{unique_filename}"
        elif submission_type == 1:
            output_dir = os.path.join('database', 'uploads', 'submissions')
            image_url = f"/api/uploads/submissions/{unique_filename}"
        else:
            raise ValueError("Invalid submission_type. Must be 0 or 1.")
        
        # Create the directory if it does not exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate the output path
        output_path = os.path.join(output_dir, unique_filename)
        
        # Save the processed image to the output path
        image.save(output_path, format="PNG")
        
        return image_url
    
    except Exception as e:
        raise Exception(f"Error processing the image: {str(e)}")

# In your submit_form function, you can now call save_image
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def submit_form(request):
    try:
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

        print("Checkpoint 1")
        # Process and save the image, return the image URL
        image_url = save_image(base64_image, 0)
                
        print("Checkpoint 2")
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
            "submission_date": datetime.datetime.now(datetime.timezone.utc),  # Current UTC time
            "last_updated_date": datetime.datetime.now(datetime.timezone.utc),  # Initially the same as submission date
            "reporter_legal_name": reporter_legal_name,
            "reporter_phone_number": reporter_phone_number,
            "updated_by": None  # Updated by will be set when an admin modifies the record
        }
        
        # Insert into MongoDB
        result = pending_list_collection.insert_one(new_record)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "updates",
            {
                "type": "new_submission",
                "message": f"New pending submission ID: {result.inserted_id}",
            }
        )

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

    return JsonResponse(_data, safe=False, json_dumps_params={'indent': 4})

# Get all records inside the collection (PendingSubmissionList)
@api_view(['GET'])
@verify_auth
def fetch_rejected_list(request, staff_email=None):
    # API to fetch all missing persons in pending list.
    _data = list(rejected_list_collection.find({}))
    for data in _data:
        data['_id'] = str(data['_id'])  
        data['reported_missing_person'] = data.get('reported_missing_person')
        data['reported_missing_location'] = data.get('reported_missing_location')
        data['reported_date_time_missing'] = data.get('reported_date_time_missing')
        data['reporter_legal_name'] = data.get('reporter_legal_name')
        data['reporter_phone_number'] = data.get('reporter_phone_number')
        data['form_status'] = data.get('form_status')
        data['rejection_reason'] = data.get('rejection_reason')
        data['last_updated_date'] = data.get('last_updated_date')
        data['submission_date'] = data.get('submission_date')
        data['updated_by'] = data.get('updated_by')

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
    person['_id'] = str(person['_id'])  
    person['reported_missing_person'] = person.get('reported_missing_person')
    person['reported_missing_location'] = person.get('reported_missing_location')
    person['reported_date_time_missing'] = person.get('reported_date_time_missing')
    person['reporter_legal_name'] = person.get('reporter_legal_name')
    person['reporter_phone_number'] = person.get('reporter_phone_number')
    person['form_status'] = person.get('form_status')
    person['last_updated_date'] = person.get('last_updated_date')
    person['submission_date'] = person.get('submission_date')
    person['updated_by'] = person.get('updated_by')

    return JsonResponse(person, safe=False, json_dumps_params={'indent': 4})

# Implement singular data fetching for pending person
@api_view(['GET'])
@verify_auth
def fetch_rejected_person(request, person_id=None, staff_email=None):
    if person_id is None:
        return JsonResponse({"error": "No person id provided."}, status=400)
    
    try:
        # Convert the string id to ObjectId
        person_object_id = ObjectId(person_id)
    except Exception as e:
        return JsonResponse({"error": f"Invalid ID format: {str(e)}"}, status=400)
    
    # Fetch the missing person based on the ID
    person = rejected_list_collection.find_one({"_id": person_object_id})

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

# [DEBUG] delete existing data inside each collection
@api_view(['DELETE'])
def delete_collection_data(request):
    try:
        # Fix the file search pattern
        file_list = glob.glob(os.path.join('database', 'uploads', '*.png')) + \
                    glob.glob(os.path.join('database', 'uploads', '*.jpg')) + \
                    glob.glob(os.path.join('database', 'uploads', '*.jpeg'))
        
        # Delete data from collections and track deletion counts
        missing_persons_deleted = missing_persons_collection.delete_many({})
        pending_list_deleted = pending_list_collection.delete_many({})
        rejected_list_deleted = rejected_list_collection.delete_many({})
        found_submission_list_deleted = found_submission_collection.delete_many({})

        total_deleted = missing_persons_deleted.deleted_count + \
                        pending_list_deleted.deleted_count + \
                        rejected_list_deleted.deleted_count + \
                        found_submission_list_deleted.deleted_count
        
        # Remove files
        for file in file_list:
            try:
                os.remove(file)
            except OSError as e:
                return JsonResponse(
                    {"error": f"Error removing file {file}: {str(e)}"},
                    status=500
                )

        # Send update to channel layer
        channel_layer = get_channel_layer()
        if total_deleted > 0:
            async_to_sync(channel_layer.group_send)(
                "updates",
                {
                    "type": "submission_update",
                    "message": f"Purged existing records and deleted {total_deleted} records.",
                }
            )
            return JsonResponse(
                {"message": f"Successfully deleted {total_deleted} records."},
                status=200
            )
        else:
            async_to_sync(channel_layer.group_send)(
                "updates",
                {
                    "type": "new_submission",
                    "message": "No existing records to purge.",
                }
            )
            return JsonResponse(
                {"message": "No records to delete."},
                status=404
            )
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )
       
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def active_search_submission(request):
    try:
        data = request.data
        person = missing_persons_collection.find_one({ '_id': ObjectId(data.get('_parent_id')) })
        
        if person is None:
            return JsonResponse({ 'error': 'This person does not exist in our records.' }, status=400)
        
        base64_image = data.get('image_url')

        # Check if image_url is a list (array) and get the first item if so
        if isinstance(base64_image, list):
            base64_image = base64_image[0]  # Get the first image in the array
        
        location_found = data.get('location_found')
        date_time_found = data.get('date_time_found')
        provided_info = data.get('provided_info')
        submission_date = datetime.datetime.now(datetime.timezone.utc)
        last_updated_date = datetime.datetime.now(datetime.timezone.utc)
        
        print(submission_date)
        print(last_updated_date)
        
        str_to_date = datetime.datetime.strptime(date_time_found, "%Y-%m-%dT%H:%M")
        formatted_date = str_to_date.strftime("%d %b. %Y, %I:%M %p")
        
        if base64_image.startswith('data:image'):
            base64_image = base64_image.split(',')[1]
            
        image_url = save_image(base64_image, 1)
        
        submission = {
            '_parent_id': ObjectId(data.get('_parent_id')),
            'image_url': image_url,
            'location_found': location_found,
            'date_time_found': formatted_date,
            'provided_info': provided_info,
            'submission_status': 'Pending',
            'submission_date': submission_date,
            'last_updated_date': last_updated_date,
            'updated_by': None
        }
        
        result = found_submission_collection.insert_one(submission)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "active_search",
            {
                "type": "active_search_message",
                "message": f"New pending active search submission ID: {id}",
            }
        )
        
        return JsonResponse({'message': 'Form submitted successfully', 'image_url': image_url}, status=200)
    except Exception as e:
        return JsonResponse({ 'message': 'Something went wrong.', 'error': str(e) }, status=500)

@verify_auth
@api_view(['GET'])
def get_active_search_submission(request, _parent_id=None, staff_email=None):
    try:
        if _parent_id is None:
            return JsonResponse({ 'error': 'Specified parent ID is null.' }, status=400)
        
        parent_object_id = ObjectId(_parent_id)
        _data = list(found_submission_collection.find({ '_parent_id': parent_object_id }))
        
        for data in _data:
            data['_id'] = str(data['_id'])
            data['_parent_id'] = str(data['_parent_id'])
            data['image_url'] = data.get('image_url')
            data['location_found'] = data.get('location_found')
            data['date_time_found'] = data.get('date_time_found')
            data['provided_info'] = data.get('provided_info')
            data['submission_status'] = data.get('submission_status')
            data['submission_date'] = data.get('submission_date')
            data['last_updated_date'] = data.get('last_updated_date')
            data['updated_by'] = data.get('updated_by')
            
        return JsonResponse(_data, safe=False, json_dumps_params={'indent': 4})
            
    except Exception as e:
        return JsonResponse({ 'message': 'Something went wrong.', 'error': str(e) }, status=500)
 
@verify_auth   
@api_view(['GET'])
def get_specific_active_search_submission(request, _parent_id=None, submission_id=None, staff_email=None):
    try:
        if submission_id is None:
            return JsonResponse({ 'error': 'Specified parent ID is null.' }, status=400)
        
        try:
            submission_object_id = ObjectId(submission_id)
            parent_object_id = ObjectId(_parent_id)
            
            print(submission_object_id)
            print(parent_object_id)
        except Exception as e:
            return JsonResponse({ 'error': f'Invalid ID format: {str(e)}' }, status=400)
        
        submission = found_submission_collection.find_one({ '_id': submission_object_id })
        
        if submission is None:
            return JsonResponse({ 'error': 'This submission ID does not exist.' }, status=400)
        
        if parent_object_id != submission.get('_parent_id'):
            return JsonResponse({ 'error': 'This submission ID is not linked to this parent ID.' }, status=400)
        
        
        submission['_id'] = str(submission.get('_id'))
        submission['_parent_id'] = str(submission.get('_parent_id'))
        
        return JsonResponse(submission, safe=False, json_dumps_params={'indent': 4})
    except Exception as e:
        return JsonResponse({ 'error': f'Something went wrong: {str(e)}' }, status=500)

@verify_auth
@api_view(['GET'])
def get_rejected_active_search_submissions(request, _parent_id=None, staff_email=None):
    try:
        if _parent_id is None:
            return JsonResponse({ 'error': 'Specified parent ID is null.' }, status=400)
        
        parent_object_id = ObjectId(_parent_id)
        _data = list(rejected_found_submission_collection.find({ '_parent_id': parent_object_id }))
        
        for data in _data:
            data['_id'] = str(data['_id'])
            data['_parent_id'] = str(data['_parent_id'])
            data['reported_location'] = data.get('reported_location')
            data['reported_datetime'] = data.get('reported_datetime')
            data['reported_information'] = data.get('reported_information')
            data['submission_status'] = data.get('submission_status')
            data['rejection_reason'] = data.get('rejection_reason')
            data['submission_date'] = data.get('submission_date')
            data['last_updated_date'] = data.get('last_updated_date')
            data['updated_by'] = data.get('updated_by')
            
        return JsonResponse(_data, safe=False, json_dumps_params={'indent': 4})
            
    except Exception as e:
        return JsonResponse({ 'message': 'Something went wrong.', 'error': str(e) }, status=500)
    
@api_view(['DELETE'])
def delete_specific_active_search_submission(request, _id=None):
    try:
        id = _id
        rejected_found_submission_collection.delete_one({ '_id': ObjectId(id) })
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "active_search",
            {
                "type": "active_search_message",
                "message": f"Deleted rejected active search submission ID: {id}",
            }
        )
        
        return JsonResponse({ 'message': 'Deleted rejected submission successfully.' }, status=200)
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )