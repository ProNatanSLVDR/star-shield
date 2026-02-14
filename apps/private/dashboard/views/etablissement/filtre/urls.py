from django.urls import path

from . import personalisation, threshold

app_name = "filtre"

urlpatterns = [
    path("threshold/", threshold.threshold_settings_view, name="threshold"),
    path("personalisation/", personalisation.personalisation_settings_view, name="personalisation"),
    path("personalisation/preview/", personalisation.personalisation_preview_view, name="personalisation_preview"),
]
