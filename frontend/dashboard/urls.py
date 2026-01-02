from django.urls import path, include
from .views import accueil

from .views.etablissements.urls import urlpatterns as etablissements_urls
from .views.etablissement.urls import urlpatterns as etablissement_urls
from .views.onboarding.urls import urlpatterns as onboarding_urls
from .views.profile.urls import urlpatterns as profile_urls
from .views.facturation.urls import urlpatterns as facturation_urls

app_name = "dashboard"

urlpatterns = [
    path("", accueil.accueil_view, name="accueil"),
    path("onboarding/", include((onboarding_urls, "onboarding"))),
    path("etablissements/", include((etablissements_urls, "etablissements"))),
    path("etablissement/", include((etablissement_urls, "etablissement"))),
    path("profile/", include((profile_urls, "profile"))),
    path("facturation/", include((facturation_urls, "facturation"))),
]
