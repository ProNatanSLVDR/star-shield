from django.urls import path

from . import historique, views

app_name = "ai_responses"

urlpatterns = [
    path("", views.ai_responses_settings_view, name="settings"),
    path("historique/", historique.historique_view, name="historique"),
    path("historique/content/", historique.historique_content_partial, name="historique_content"),
]
