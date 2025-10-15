from django.urls import path
from . import views

app_name = "gmb_management"

urlpatterns = [
    path('', views.management_view, name='index'),
    path('add/', views.add_etablissement_view, name='add'),
]
