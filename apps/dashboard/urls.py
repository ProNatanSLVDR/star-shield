from django.urls import path
from .views import views

app_name = "dashboard"

urlpatterns = [
    path('', views.accueil_view, name='accueil'),
]
