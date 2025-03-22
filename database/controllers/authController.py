import json
import bcrypt
import jwt
from functools import wraps
from django.conf import settings
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import os

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_DB_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
staff_collection = db["StaffTB"]
SECRET_KEY = settings.SECRET_KEY

@csrf_exempt
def staff_signup(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        department = data.get("department")

        # Check if email already exists
        if staff_collection.find_one({"email": email}):
            return JsonResponse({"error": "Email already exists"}, status=400)

        # Check password match
        if password != confirm_password:
            return JsonResponse({"error": "Passwords do not match"}, status=400)

        # Hash password before storing
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Create new staff record
        staff_collection.insert_one({
            "email": email,
            "password": hashed_password,
            "department": department,
            "role": "staff",
            "signupdate": datetime.datetime.utcnow()
        })

        return JsonResponse({"message": "Signup successful"}, status=201)
# staff login details
@csrf_exempt
def staff_login(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")

            # Check if email exists
            staff = staff_collection.find_one({"email": email})
            if not staff:
                print("ERROR: Email not found")
                return JsonResponse({"error": "Invalid email or password"}, status=401)

            # Ensure password is stored as a hashed string
            stored_password = staff["password"].encode()

            # Check password using bcrypt
            if not bcrypt.checkpw(password.encode(), stored_password):
                print("ERROR: Password does not match")
                return JsonResponse({"error": "Invalid email or password"}, status=401)

            # Generate JWT token
            payload = {
                "email": email,
                "role": staff["role"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

            print(" Login successful")  
            return JsonResponse({"message": "Login successful", "token": token}, status=200)

        except Exception as e:
            print(f" ERROR: {e}")  # Print the actual error
            return JsonResponse({"error": str(e)}, status=500)

#  Dash board detail
def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JsonResponse({"error": "Unauthorized - No Authorization header provided"}, status=401)
            # Ensure correct format
            parts = auth_header.split(" ")
            if len(parts) != 2 or parts[0] != "Bearer":
                return JsonResponse({"error": "Unauthorized - Invalid token format"}, status=401)

            token = parts[1]
            # Decode token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            email = payload.get("email")

            staff = staff_collection.find_one({"email": email})
            if not staff or staff.get("role") != "staff":
                return JsonResponse({"error": "Forbidden - Staff access required"}, status=403)

            return view_func(request, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Unauthorized - Token expired"}, status=401)
        except jwt.DecodeError:
            return JsonResponse({"error": "Unauthorized - Invalid token"}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return wrapper

# Staff Dashboard Route
@staff_required
def staff_dashboard(request):
    """Fetch pending submissions for review."""
    try:
        pending_forms = list(db["MissingPersonsList"].find({"form_status": "Pending"}, {"_id": 0}))

        return JsonResponse(
            {
                "message": "Pending submissions retrieved successfully",
                "pending_forms": pending_forms,
            },
            status=200,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
