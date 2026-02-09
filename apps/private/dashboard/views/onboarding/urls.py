from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("welcome/", views.welcome_view, name="welcome"),
    path("how-it-works/", views.how_it_works_view, name="how_it_works"),
    path("threshold/", views.threshold_view, name="threshold"),
    path("roulette/", views.roulette_view, name="roulette"),
    path("ai-responses/", views.ai_responses_view, name="ai_responses"),
    path("connect-google/", views.connect_google_view, name="connect_google"),
    path("reconnect-google/", views.reconnect_google_view, name="reconnect_google"),
    path("import-etablissements/", views.import_etablissements_view, name="import_etablissements"),
    path("complete/", views.complete_view, name="complete"),
    path("skip/", views.skip_onboarding_view, name="skip"),
]
