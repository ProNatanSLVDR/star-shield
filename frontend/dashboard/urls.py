from django.urls import path, include
from .views import accueil

from .views.etablissements.urls import urlpatterns as etablissements_urls
from .views.etablissement.urls import urlpatterns as etablissement_urls
from .views.onboarding.urls import urlpatterns as onboarding_urls

app_name = "dashboard"

urlpatterns = [
    path("", accueil.accueil_view, name="accueil"),
    path("onboarding/", include((onboarding_urls, "onboarding"))),
    path("etablissements/", include((etablissements_urls, "etablissements"))),
    path("etablissement/", include((etablissement_urls, "etablissement"))),
]
