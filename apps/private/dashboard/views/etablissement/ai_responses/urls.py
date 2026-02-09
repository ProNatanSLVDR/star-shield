from django.urls import path

from . import historique, pending, views

app_name = "ai_responses"

urlpatterns = [
    path("", views.ai_responses_settings_view, name="settings"),
    path("historique/", historique.historique_view, name="historique"),
    path("historique/content/", historique.historique_content_partial, name="historique_content"),
    path("pending/", pending.pending_view, name="pending"),
    path("pending/content/", pending.pending_content_partial, name="pending_content"),
    path("pending/<int:review_id>/approve/", pending.approve_review_view, name="pending_approve"),
    path("pending/<int:review_id>/reject/", pending.reject_review_view, name="pending_reject"),
    path("pending/<int:review_id>/regenerate/", pending.regenerate_review_view, name="pending_regenerate"),
]
