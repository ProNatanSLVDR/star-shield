from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import errorviews

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auths/', include(('auths.urls', 'auths'), namespace='auths')),
    path('accounts/', include('allauth.urls')),
    path('', include(('apps.dashboard.urls', 'dashboard'), namespace='dashboard')),
    path('', include('django_components.urls')),

    path('error/404/', errorviews.error_404_preview, name='error_404_preview'),
    path('error/500/', errorviews.error_500_preview, name='error_500_preview'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = "errorviews.error_404"
handler500 = "errorviews.error_500"


