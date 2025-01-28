from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.views import View
from backend.models.missingPersonModel import MissingPerson
import base64
import os
import uuid
from PIL import Image
from io import BytesIO


@csrf_exempt
def submit_form(request):
    if request.method == 'POST':
        try:
            # Parse the request body (assuming JSON input)
            data = request.POST
            image = request.FILES.get('image')

            # Extract fields
            name = data.get('name')
            age = data.get('age')
            last_location_seen = data.get('last_location_seen')
            last_date_time_seen = data.get('last_date_time_seen')
            additional_info = data.get('additional_info')

            # Validate fields
            if not name or not age or not last_location_seen or not last_date_time_seen or not image:
                return JsonResponse({
                    'message': 'Ensure all required fields (name, age, last_location_seen, last_date_time_seen, image) are provided'
                }, status=400)

            # Process the image (resize and save)
            image_extension = image.name.split('.')[-1]
            unique_filename = f"{uuid.uuid4().hex}.{image_extension}"
            output_path = os.path.join('uploads', unique_filename)

            with Image.open(image) as img:
                img = img.resize((200, 200), Image.ANTIALIAS)
                img.save(output_path)

            # Save the record in the database
            MissingPerson.objects.create(
                name=name,
                age=int(age),
                last_location_seen=last_location_seen,
                last_date_time_seen=last_date_time_seen,
                additional_info=additional_info,
                image=output_path
            )
            return JsonResponse({'message': 'Form submitted successfully'}, status=200)

        except Exception as e:
            return JsonResponse({
                'message': 'Something went wrong with the process',
                'error': str(e)
            }, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
