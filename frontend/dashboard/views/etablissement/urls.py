from django.urls import path, include
from . import views
from .settings import urls as settings_urls

app_name = "etablissement"

urlpatterns = [
    path("", views.overview_view, name="overview"),
    path("avis/", views.avis_view, name="avis"),
    path("refresh/", views.refresh_reviews_view, name="refresh"),
    path("settings/", include(settings_urls)),
]
