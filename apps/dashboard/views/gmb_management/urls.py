from django.urls import path
from . import views

app_name = "gmb_management"

urlpatterns = [
    path('', views.gmb_management_view, name='test'),
]
