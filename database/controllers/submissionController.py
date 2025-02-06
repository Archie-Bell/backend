import os
import time
from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from database.controllers.formController import submit_form
from database.controllers.notificationController import push_notifications

@csrf_exempt
def upload_image(request):
    if request.method == "POST" and request.FILES.get('image'):
        try:
            image = request.FILES['image']
            allowed_mime_types = ['image/png', 'image/jpg', 'image/jpeg']

            if image.content_type not in allowed_mime_types:
                return JsonResponse({'message': 'Only image files are allowed'}, status=400)

            # Save image with a random filename
            file_name = f"{image.name.split('.')[0]}_{int(time.time())}.{image.name.split('.')[-1]}"
            file_path = default_storage.save(f"uploads/{file_name}", image)

            # Call the form submission and notification logic
            submit_form(request)  # Adjust this to handle form data
            push_notifications(request)  # Adjust this for sending notifications

            return JsonResponse({'message': 'File uploaded successfully', 'file_path': file_path}, status=200)

        except Exception as e:
            return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)
    return JsonResponse({'message': 'Invalid request'}, status=400)

def serve_image(request, image_name):
    image_path = os.path.join(settings.MEDIA_ROOT, 'uploads', image_name)
    if os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')
    return JsonResponse({'message': 'File not found'}, status=404)
