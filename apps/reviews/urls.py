from django.urls import path
from .views import (
    google_auth_callback,
    google_auth_start,
    feedback_thanks_view,
    feedback_view,
)

app_name = "reviews"

urlpatterns = [
    path('google_auth/start/', google_auth_start, name='google_auth_start'),
    path('google_auth/callback/', google_auth_callback, name='google_auth_callback'),
    path('feedback/<str:identifier>/', feedback_view, name='feedback'),
    path('feedback/<str:identifier>/thanks/', feedback_thanks_view, name='feedback_thanks'),
]
