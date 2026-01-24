from django.urls import path

from . import roulette

app_name = "roulette"

urlpatterns = [
    path("", roulette.roulette_settings_view, name="roulette"),
]
