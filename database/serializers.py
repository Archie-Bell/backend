from rest_framework import serializers
from database.models import StaffTB

class StaffSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = StaffTB
        fields = ["email", "password", "confirm_password", "department", "role", "signupdate"]
        extra_kwargs = {
            "password": {"write_only": True},
            "signupdate": {"read_only": True},
            "role": {"read_only": True}  # Prevent role modification in signup
        }

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match!"})
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")  # Remove confirm_password before saving
        staff = StaffTB.objects.create_staff(
            email=validated_data["email"],
            password=validated_data["password"],
            department=validated_data["department"],
        )
        return staff




# from rest_framework import serializers
# from database.models import MissingPerson

# class MissingPersonSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MissingPerson
#         fields = '__all__'  # Serialize all fields
