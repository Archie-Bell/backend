import os
from django.conf import settings
from django.http import FileResponse, HttpResponse, HttpResponseNotFound
from mimetypes import guess_type

def fetch_image_data(request, image_name):
    try:
        """ Serve images from 'database/uploads/' via API """
        print("Attempting to display image.")
        image_path = os.path.join(settings.BASE_DIR, "database/uploads", image_name)
        print(image_path)

        # Check if file exists
        if os.path.exists(image_path):
            # Guess MIME type based on file extension
            mime_type, _ = guess_type(image_path)
            
            if not mime_type:
                mime_type = 'application/octet-stream'  # Fallback MIME type

            return FileResponse(open(image_path, "rb"), content_type=mime_type)
        
        return HttpResponseNotFound("<h1>404 - Image Not Found</h1>")
    
    except Exception as e:
        return HttpResponse(f'Something went wrong: {str(e)}', status=500)
