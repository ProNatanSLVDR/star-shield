from django.urls import path

from . import views

app_name = "etablissements"

urlpatterns = [
    path("", views.list_etablissements_view, name="list"),
    path("import/", views.import_etablissement_partial, name="import_partial"),
    path("details/<int:id>/", views.etablissement_details_partial, name="details_partial"),
    path("delete/<int:id>/", views.delete_etablissement_confirmation_partial, name="delete_partial"),
    # Toggle status (Activate/Deactivate)
    path("toggle-status/<int:id>/", views.toggle_etablissement_status_partial, name="toggle_status_partial"),
    path("toggle-status/<int:id>/confirm/", views.toggle_etablissement_status, name="toggle_status"),
    # Change plan
    path("change-plan/<int:id>/", views.change_plan_partial, name="change_plan_partial"),
    path("change-plan/<int:id>/confirm/", views.change_plan, name="change_plan"),
    # Selection d'un établissement
    path("select/<int:id>/", views.select_etablissement, name="select"),
    path("unselect/", views.unselect_etablissement, name="unselect"),
    path("selector-partial/", views.etablissement_selector_partial, name="selector_partial"),
]
