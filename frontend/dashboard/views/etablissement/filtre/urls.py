from django.urls import path
from . import threshold, personalisation, qrcode

app_name = "filtre"

urlpatterns = [
    path("threshold/", threshold.threshold_settings_view, name="threshold"),
    path("personalisation/", personalisation.personalisation_settings_view, name="personalisation"),
    path("qrcode/", qrcode.qr_code_settings_view, name="qrcode"),
]
