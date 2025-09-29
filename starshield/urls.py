from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('auths.urls', namespace='auths')),
    path('', include('django_components.urls')),
]
