from django.urls import path
from django.http import JsonResponse
from . import views


def hello(request):
    return JsonResponse({"message": "Hello from the API!"})

# URL Config
urlpatterns = [
    # path('hello/', views.say_hello)
     path('hello/', hello, name='hello'),
]