from django.urls import path

from . import views

app_name = "settings"

urlpatterns = [
    path("toggle-feature/", views.toggle_feature_view, name="toggle_feature"),
    path("toggle-single-feature/", views.toggle_single_feature_view, name="toggle_single_feature"),
]
