from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/submission-updates/', consumers.SubmissionConsumer.as_asgi()),
    re_path(r'ws/active-search-updates/', consumers.ActiveSearchConsumer.as_asgi())
]