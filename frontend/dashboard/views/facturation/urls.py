from django.urls import path
from . import views

app_name = "facturation"

urlpatterns = [
    path("", views.facturation_view, name="facturation"),
]


