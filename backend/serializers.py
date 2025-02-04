from rest_framework import serializers
from backend.models.missingPersonModel import MissingPerson

class MissingPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissingPerson
        fields = '__all__'  # Serialize all fields
