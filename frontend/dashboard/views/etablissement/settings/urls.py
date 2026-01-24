from django.urls import path

from . import views

app_name = "settings"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("toggle-feature/", views.toggle_feature_view, name="toggle_feature"),
]
