from django.urls import path
from .views import google_auth_start, google_auth_callback

app_name = "reviews"

urlpatterns = [
    path('google_auth/start/', google_auth_start, name='google_auth_start'),
    path('google_auth/callback/', google_auth_callback, name='google_auth_callback'),
]
