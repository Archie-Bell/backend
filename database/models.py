from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.timezone import now
# Create your models here
class MissingPerson(models.Model):
    name = models.CharField(max_length=255)
    age = models.IntegerField()
    last_location_seen = models.CharField(max_length=255)
    last_date_time_seen = models.DateTimeField()
    additional_info = models.TextField(blank=True, null=True)
    image_url = models.CharField(max_length=500)  # Storing image URL
    reporter_legal_name = models.CharField(max_length=255, blank=True, null=True)# Reporter Name
    reporter_phone_number = models.CharField(max_length=20, blank=True, null=True)# Phone Number
    rejection_reason = models.TextField(blank=True, null=True)# Reason for rejection
    form_status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending")
    submission_date = models.DateTimeField(default=now)  # Auto set when submitted
    last_updated_date = models.DateTimeField(auto_now=True)  # Auto update when modified
    updated_by = models.CharField(max_length=255, blank=True, null=True)  # To store admin name who updates

    def __str__(self):
        return self.name


# Custom User Manager
class StaffManager(BaseUserManager):
    def create_staff(self, email, password=None, department="General", role="staff"):
        if not email:
            raise ValueError("Staff must have an email address")
        staff = self.model(email=self.normalize_email(email), department=department, role=role)
        staff.set_password(password)  # Hash password
        staff.save(using=self._db)
        return staff

# Staff Table (StaffTB)
class StaffTB(AbstractBaseUser):
    email = models.EmailField(unique=True)  # Unique email
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=[("staff", "Staff"), ("admin", "Admin")], default="staff")
    signupdate = models.DateTimeField(default=now)  # Auto-filled on creation

    # Required for authentication
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["department"]

    objects = StaffManager()

    def __str__(self):
        return f"{self.email} ({self.role})"
