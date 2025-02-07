from django.urls import path
from django.http import JsonResponse
from . import views

from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from database.controllers.formController import submit_form, get_missing_persons
from database.controllers.notificationController import push_notifications
from database.controllers.submissionController import upload_image, serve_image
from django.urls import path

# URL Config
urlpatterns = [
    #  path('submit-form/', submit_form, name='submit_form'),
    #   path('push-notifications/', push_notifications, name='push_notifications'),
    path('uploads/<str:image_name>/', serve_image, name='serve_image'),
     
    path('missing-persons/', get_missing_persons, name='get_missing_persons'),
    path('missing-persons/create', submit_form, name='submit_form'),
    path('send-notification/', push_notifications, name='send_notification'),
] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
