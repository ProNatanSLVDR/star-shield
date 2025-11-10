from django.urls import path, include
from . import views
from .settings import urls as settings_urls

app_name = "etablissement"

urlpatterns = [
    path("", views.overview_view, name="overview"),
    path("settings/", include(settings_urls)),
]
