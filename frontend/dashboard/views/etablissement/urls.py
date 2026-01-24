from django.urls import include, path

from . import views
from .filtre import urls as filtre_urls
from .roulette import urls as roulette_urls
from .settings import urls as settings_urls

app_name = "etablissement"

urlpatterns = [
    path("", views.overview_view, name="overview"),
    path("avis/", views.avis_view, name="avis"),
    path("refresh/", views.refresh_reviews_view, name="refresh"),
    path("settings/", include(settings_urls)),
    path("filtre/", include(filtre_urls)),
    path("roulette/", include(roulette_urls)),
]
