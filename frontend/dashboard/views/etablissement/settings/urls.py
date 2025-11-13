from django.urls import path
from . import views

app_name = "settings"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("reviews/", views.reviews_settings_view, name="reviews"),
    path("calculator/", views.threshold_objective_calculator_view, name="calculator"),
]

