from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import errorviews

urlpatterns = [
    # Django
    path("admin/", admin.site.urls),
    path("", include("django_components.urls")),
    # auths
    path("accounts/", include("allauth.urls")),
    path("auths/", include("auths.urls")),
    # Apps
    path("", include(("frontend.dashboard.urls", "dashboard"))),
    path("reviews/", include(("frontend.reviews.urls", "reviews"))),
    path("roulette/", include(("frontend.roulette.urls", "roulette"))),
    path("payments/", include("payments.urls")),
    # Errors
    path("error_preview/404/", errorviews.error_404_preview, name="error_404_preview"),
    path("error_preview/500/", errorviews.error_500_preview, name="error_500_preview"),
]
# Serve media files in development (when not using GCS)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Handlers
handler404 = "starshield.errorviews.error_404"
handler500 = "starshield.errorviews.error_500"
