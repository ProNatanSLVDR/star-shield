from django.urls import path

from .views import google_gmb_callback, google_gmb_start

app_name = "auths"

urlpatterns = [
    path("google_gmb/start/", google_gmb_start, name="google_gmb_start"),
    path("google_gmb/callback/", google_gmb_callback, name="google_gmb_callback"),
]
