from django.urls import path
from . import views

app_name = "etablissement"

urlpatterns = [
    path('', views.overview_view, name='overview'),
]
