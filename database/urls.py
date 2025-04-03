from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from database.controllers.formController import fetch_pending_person, submit_form, fetch_pending_list, delete_collection_data, fetch_missing_person_list, fetch_missing_person, fetch_rejected_list, fetch_rejected_person, active_search_submission, get_active_search_submission, get_specific_active_search_submission, get_rejected_active_search_submissions, delete_specific_active_search_submission
from database.controllers.authController import staff_signup, staff_login, verify_panel_access
from database.controllers.imageController import fetch_image_data
from database.controllers.updateController import update_submission, handle_active_search_submission


urlpatterns = [
    path('missing-persons/pending/', fetch_pending_list, name='get_pending_list'),
    path('missing-person/pending/<str:person_id>/', fetch_pending_person, name='get_pending_person'),
    path('missing-persons/', fetch_missing_person_list, name='get_missing_persons'),
    path('missing-person/<str:person_id>/', fetch_missing_person, name='get_missing_person'),
    path('missing-persons/rejected/', fetch_rejected_list, name='get_rejected_list'),
    path('missing-person/rejected/<str:person_id>/', fetch_rejected_person, name='get_rejected_person'),
    path('missing-persons/create/', submit_form, name='submit_form'),
    path("staff/signup/", staff_signup, name="staff_signup"),
    path("staff/login/", staff_login, name="staff_login"),  
    path('staff/verify/', verify_panel_access, name='verify_panel_access'),
    path("debug/purge-data", delete_collection_data, name='delete_collection_data'),
    path('uploads/<str:image_name>', fetch_image_data, name='fetch_image_data'),
    path('staff/submission/update/', update_submission, name='update_submission'),
    path('missing-person/submission', active_search_submission, name='person_found_submission'),
    path('staff/missing-person/submissions/rejected/purge/<str:_id>', delete_specific_active_search_submission, name='delete_specific_rejected_found_submissions'),
    path('staff/missing-person/submissions/rejected/<str:_parent_id>', get_rejected_active_search_submissions, name='get_rejected_found_submissions'),
    path('staff/missing-person/submissions/<str:_parent_id>', get_active_search_submission, name='get_found_submission'),
    path('staff/missing-person/submissions/<str:_parent_id>/<str:submission_id>', get_specific_active_search_submission, name='get_specific_found_submission'),
    path('staff/missing-person/update/', handle_active_search_submission, name='handle_found_submission')
]

# Serve uploaded images in development mode
if settings.DEBUG:
    urlpatterns += static(settings.UPLOADS_URL, document_root=settings.UPLOADS_ROOT)
