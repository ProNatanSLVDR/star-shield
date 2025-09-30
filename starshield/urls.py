from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include(('apps.account.urls', 'account'), namespace='account')),
    path('', include('django_components.urls')),
]
