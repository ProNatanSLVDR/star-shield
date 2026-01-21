from django.urls import path, include
from . import views
from .settings import urls as settings_urls
from .filtre import urls as filtre_urls
from .roulette import urls as roulette_urls

app_name = "etablissement"

urlpatterns = [
    path("", views.overview_view, name="overview"),
    path("avis/", views.avis_view, name="avis"),
    path("refresh/", views.refresh_reviews_view, name="refresh"),
    path("settings/", include(settings_urls)),
    path("filtre/", include(filtre_urls)),
    path("roulette/", include(roulette_urls)),
]
