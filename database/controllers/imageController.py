import os
from django.conf import settings
from django.http import FileResponse, HttpResponse, HttpResponseNotFound

def fetch_image_data(request, image_name):
    try:
        """ Serve images from 'database/uploads/' via API """
        print("Attempting to display image.")
        image_path = os.path.join(settings.BASE_DIR, "database/uploads", image_name)
        print(image_path)

        if os.path.exists(image_path):
            return FileResponse(open(image_path, "rb"), content_type="image/jpeg" or "image/jpg" or "image/png")

        return HttpResponseNotFound("<h1>404 - Image Not Found</h1>")
    except Exception as e:
        return HttpResponse(f'Something went wrong: {str(e)}', status=500)
