from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("feedback/<str:identifier>/", views.feedback_view, name="feedback"),
    path(
        "feedback/<str:identifier>/internal/",
        views.internal_feedback_view,
        name="internal_feedback",
    ),
    path(
        "feedback/<str:identifier>/external/",
        views.external_feedback_view,
        name="external_feedback",
    ),
    path(
        "feedback/<str:identifier>/thanks/",
        views.feedback_thanks_view,
        name="feedback_thanks",
    ),
    path("qr/<str:identifier>/", views.qr_code_image_view, name="qr_code"),
]
