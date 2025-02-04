from rest_framework.response import Response
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from backend.models.missingPersonModel import MissingPerson
from backend.serializers import MissingPersonSerializer
from PIL import Image
import os
import uuid
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Ensure it handles file uploads
def submit_form(request):
    try:
        # Ensure 'image' is in FILES
        if 'image' not in request.FILES:
            return Response({'error': 'Image file is required'}, status=400)

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
            return Response({'message': 'All fields are required!'}, status=400)

        # Save the image
        image_extension = image.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4().hex}.{image_extension}"
        output_dir = os.path.join('backend', 'uploads')
        os.makedirs(output_dir, exist_ok=True)  # Ensure folder exists
        output_path = os.path.join(output_dir, unique_filename)

        with open(output_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)

        # Save record in database
        MissingPerson.objects.create(
            name=name,
            age=int(age),
            last_location_seen=last_location_seen,
            last_date_time_seen=last_date_time_seen,
            additional_info=additional_info,
            image=output_path  # Save file path
        )

        return Response({'message': 'Form submitted successfully'}, status=200)

    except Exception as e:
        return Response({'message': 'Something went wrong', 'error': str(e)}, status=500)



@api_view(['GET'])
def get_missing_persons(request):
    """
    API to fetch all missing persons.
    """
    persons = MissingPerson.objects.all()
    serializer = MissingPersonSerializer(persons, many=True)
    return Response(serializer.data)
