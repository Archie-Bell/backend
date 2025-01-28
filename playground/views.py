from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
# REQUEST -> RESPONSE

def say_hello(request):
    return HttpResponse('Hello, world.')
