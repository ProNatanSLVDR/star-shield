from django.urls import path, include
from .views import accueil
from .views.etablissements.urls import urlpatterns as etablissements_urls
from .views.etablissement.urls import urlpatterns as etablissement_urls
app_name = "dashboard"

urlpatterns = [
    path('', accueil.accueil_view, name='accueil'),
    path('etablissements/', include((etablissements_urls, 'etablissements'))),
    path('etablissement/', include((etablissement_urls, 'etablissement'))),
]
