from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from initiate_db_connect import collection

from PIL import Image
import os
import uuid

@api_view(['POST'])
# @parser_classes([MultiPartParser, FormParser])  # Ensure it handles file uploads
def submit_form(request):
    try:
        # Ensure 'image' is in FILES
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'Image file is required'}, status=400)

        # Extract fields
        data = request.data  
        image = request.FILES['image']

        name = data.get('name')
        age = data.get('age')
        last_location_seen = data.get('last_location_seen')
        last_date_time_seen = data.get('last_date_time_seen')
        additional_info = data.get('additional_info')

        # Validate fields
        if not all([name, age, last_location_seen, last_date_time_seen, image]):
            return JsonResponse({'message': 'All fields are required'}, status=400)

        # Save the image
        
        # TODO: This method is not safe, Aishat. - gobrin3707
        image_extension = image.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4().hex}.{image_extension}"
        output_dir = os.path.join('database', 'uploads')
        os.makedirs(output_dir, exist_ok=True)  # Ensure folder exists
        output_path = os.path.join(output_dir, unique_filename)

        with open(output_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)

        # Save record in database
        collection.insert_one({
            "name": name,
            "age": int(age),
            "last_location_seen": last_location_seen,
            "last_date_time_seen": last_date_time_seen,
            "additional_info": additional_info,
            # "image": image
        })

        return JsonResponse({'message': 'Form submitted successfully'}, status=200)

    except Exception as e:
        return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)


    # SNIPPET CODE

    # try:
    #     _data = request.data
    #     name = _data.get('name')

    #     return JsonResponse({'name': name})
    # except Exception as e:
    #     return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)



# Get all records inside the collection
@api_view(['GET'])
def get_missing_persons(request):
    """
    API to fetch all missing persons.
    """

    # Store data temporarily
    _data = list(collection.find({}))

    # Make _id readable when displaying as JSON
    for data in _data:
        data['_id'] = str(data['_id'])

    return JsonResponse(_data, safe=False, json_dumps_params={'indent': 4})
