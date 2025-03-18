from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from database.controllers.formController import submit_form, get_missing_persons
from database.controllers.notificationController import push_notifications
from database.controllers.submissionController import serve_image
from database.controllers.authController import staff_signup, staff_login,staff_dashboard
from database.controllers.updateController import update_submission
urlpatterns = [
    path('missing-persons/', get_missing_persons, name='get_missing_persons'),
    path('missing-persons/create/', submit_form, name='submit_form'),
    path('send-notification/', push_notifications, name='send_notification'),
    path("api/uploads/<str:image_name>/", serve_image, name="serve_image"),
    path("staff/signup/", staff_signup, name="staff_signup"),
    path("staff/login/", staff_login, name="staff_login"),  
    path("staff/update_submission/", update_submission, name="update_submission"),
    path("staff/dashboard/", staff_dashboard, name="staff_dashboard"),
    
]


# Serve uploaded images in development mode
if settings.DEBUG:
    urlpatterns += static(settings.UPLOADS_URL, document_root=settings.UPLOADS_ROOT)
