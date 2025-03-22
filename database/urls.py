from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from database.controllers.formController import submit_form, get_missing_persons, delete_collection_data
from database.controllers.submissionController import serve_image
from database.controllers.authController import staff_signup, staff_login,staff_dashboard
from database.controllers.updateController import update_submission

urlpatterns = [
    path('missing-persons/', get_missing_persons, name='get_missing_persons'),
    path('missing-persons/create/', submit_form, name='submit_form'),
    path("uploads/<str:image_name>/", serve_image, name="serve_image"),
    path("staff/signup/", staff_signup, name="staff_signup"),
    path("staff/login/", staff_login, name="staff_login"),  
    path("staff/update_submission/", update_submission, name="update_submission"),
    path("staff/dashboard/", staff_dashboard, name="staff_dashboard"),
    path("debug/purge-data", delete_collection_data, name='delete_collection_data')
]


# Serve uploaded images in development mode
if settings.DEBUG:
    urlpatterns += static(settings.UPLOADS_URL, document_root=settings.UPLOADS_ROOT)
