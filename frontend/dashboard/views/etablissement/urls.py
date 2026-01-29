from django.urls import include, path

from . import qrcodes, views
from .filtre import urls as filtre_urls
from .roulette import urls as roulette_urls
from .settings import urls as settings_urls

app_name = "etablissement"

urlpatterns = [
    path("", views.overview_view, name="overview"),
    path("stats/", views.stats_view, name="stats"),
    path("avis/", views.avis_view, name="avis"),
    path("refresh/", views.refresh_reviews_view, name="refresh"),
    path("settings/", include(settings_urls)),
    path("filtre/", include(filtre_urls)),
    path("roulette/", include(roulette_urls)),
    # QR Codes
    path("qrcodes/", qrcodes.qr_code_management_view, name="qrcodes"),
    path("qrcodes/create/", qrcodes.qr_code_create_view, name="qrcode_create"),
    path("qrcodes/<int:qr_code_id>/delete/", qrcodes.qr_code_delete_partial, name="qrcode_delete_partial"),
    path("qrcodes/image/<str:identifier>/", qrcodes.qr_code_image_view, name="qr_code"),
]
