from django.urls import path
from . import views

app_name = "settings"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("reviews/", views.personalisation_settings_view, name="reviews"),
    path("threshold/", views.threshold_settings_view, name="threshold"),
    path("qrcode/", views.qr_code_settings_view, name="qrcode"),
    path("roulette/", views.roulette_settings_view, name="roulette"),
]
