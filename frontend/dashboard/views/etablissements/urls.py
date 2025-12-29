from django.urls import path
from . import views

app_name = "etablissements"

urlpatterns = [
    path('', views.list_etablissements_view, name='list'),
    path('import/', views.import_etablissement_partial, name='import_partial'),
    path('delete/<int:id>/', views.delete_etablissement_confirmation_partial, name='delete_partial'),


    # Selection d'un établissement
    path('select/<int:id>/', views.select_etablissement, name='select'),
    path('unselect/', views.unselect_etablissement, name='unselect'),
    path('selector-partial/', views.etablissement_selector_partial, name='selector_partial'),
]
