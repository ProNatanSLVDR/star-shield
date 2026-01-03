from django.urls import path
from . import views

app_name = "etablissements"

urlpatterns = [
    path('', views.list_etablissements_view, name='list'),
    path('import/', views.import_etablissement_partial, name='import_partial'),
    path('delete/<int:id>/', views.delete_etablissement_confirmation_partial, name='delete_partial'),
    
    # Activation d'un établissement
    path('activate/<int:id>/', views.activate_etablissement_partial, name='activate_partial'),
    path('activate/<int:id>/confirm/', views.activate_etablissement, name='activate'),
    
    # Désactivation d'un établissement
    path('deactivate/<int:id>/', views.deactivate_etablissement_partial, name='deactivate_partial'),
    path('deactivate/<int:id>/confirm/', views.deactivate_etablissement, name='deactivate'),

    # Selection d'un établissement
    path('select/<int:id>/', views.select_etablissement, name='select'),
    path('unselect/', views.unselect_etablissement, name='unselect'),
    path('selector-partial/', views.etablissement_selector_partial, name='selector_partial'),
]
