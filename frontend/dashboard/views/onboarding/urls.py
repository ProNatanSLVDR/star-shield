from django.urls import path
from . import views

app_name = "onboarding"

urlpatterns = [
    path("welcome/", views.welcome_view, name="welcome"),
    path("how-it-works/", views.how_it_works_view, name="how_it_works"),
    path("connect-google/", views.connect_google_view, name="connect_google"),
    path("reconnect-google/", views.reconnect_google_view, name="reconnect_google"),
    path("import-etablissements/", views.import_etablissements_view, name="import_etablissements"),
    path("complete/", views.complete_view, name="complete"),
    path("skip/", views.skip_onboarding_view, name="skip"),
]
