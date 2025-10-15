from django.urls import path, include
from .views import accueil
from .views.gmb_management.urls import urlpatterns as gmb_management_urls

app_name = "dashboard"

urlpatterns = [
    path('', accueil.accueil_view, name='accueil'),
    path('gmb-management/', include((gmb_management_urls, 'gmb_management'))),
]
