from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from database.controllers.formController import fetch_pending_person, submit_form, fetch_pending_list, delete_collection_data, fetch_missing_person_list, fetch_missing_person
from database.controllers.authController import staff_signup, staff_login, verify_panel_access
from database.controllers.imageController import fetch_image_data
from database.controllers.updateController import update_submission


urlpatterns = [
    path('missing-persons/pending/', fetch_pending_list, name='get_pending_list'),
    path('missing-person/pending/<str:person_id>/', fetch_pending_person, name='get_pending_person'),
    path('missing-persons/', fetch_missing_person_list, name='get_missing_persons'),
    path('missing-person/<str:person_id>/', fetch_missing_person, name='get_missing_person'),
    path('missing-persons/create/', submit_form, name='submit_form'),
    path("staff/signup/", staff_signup, name="staff_signup"),
    path("staff/login/", staff_login, name="staff_login"),  
    path('staff/verify/', verify_panel_access, name='verify_panel_access'),
    path("debug/purge-data", delete_collection_data, name='delete_collection_data'),
    path('uploads/<str:image_name>', fetch_image_data, name='fetch_image_data'),
    path('staff/submission/update/', update_submission, name='update_submission')
]


# Serve uploaded images in development mode
if settings.DEBUG:
    urlpatterns += static(settings.UPLOADS_URL, document_root=settings.UPLOADS_ROOT)
