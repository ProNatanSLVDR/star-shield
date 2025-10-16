from django.urls import path
from . import views

app_name = "etablissements"

urlpatterns = [
    path('', views.list_etablissements_view, name='list'),
    path('partial/', views.list_etablissements_partial_view, name='list_partial'),
    path('import/', views.import_etablissement_partial_view, name='import_partial'),
]
