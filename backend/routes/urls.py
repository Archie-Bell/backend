"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from backend.controllers.formController import submit_form
from backend.controllers.notificationController import push_notifications
from backend.controllers.submissionController import upload_image, serve_image
from django.urls import path
from backend.controllers.formController import submit_form, get_missing_persons
from backend.controllers.notificationController import push_notifications


def home(request):
    return HttpResponse("Welcome to the backend home page!")
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('playground.urls')),
    #  path('submit-form/', submit_form, name='submit_form'),
    #   path('push-notifications/', push_notifications, name='push_notifications'),
      path('api/uploads/<str:image_name>/', serve_image, name='serve_image'),
     path('', home),  # Root URL path
     
    path('api/missing-persons/', get_missing_persons, name='get_missing_persons'),
    path('api/missing-persons/create/', submit_form, name='submit_form'),
    path('api/send-notification/', push_notifications, name='send_notification'),
] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
