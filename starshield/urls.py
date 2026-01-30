from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import errorviews

urlpatterns = [
    # Admin and Hijack
    path("admin/", admin.site.urls),
    path("hijack/", include("hijack.urls")),
    path("", include("django_components.urls")),
    # Auth
    path("accounts/", include("allauth.urls")),
    path("auths/", include("apps.private.auths.urls")),
    # Private apps
    path("", include(("apps.private.dashboard.urls", "dashboard"))),
    path("payments/", include("apps.private.payments.urls")),
    # Public apps
    path("reviews/", include(("apps.public.reviews.urls", "reviews"))),
    path("roulette/", include(("apps.public.roulette.urls", "roulette"))),
    path("", include(("apps.public.routing.urls", "routing"))),
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
