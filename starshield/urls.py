from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include(('apps.account.urls', 'account'), namespace='account')),
    path('', include(('apps.dashboard.urls', 'dashboard'), namespace='dashboard')),
    path('', include('django_components.urls')),
]
