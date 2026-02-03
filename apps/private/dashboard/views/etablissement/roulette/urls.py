from django.urls import path

from . import roulette

app_name = "roulette"

urlpatterns = [
    path("", roulette.roulette_settings_view, name="roulette"),
    path("prizes/table/", roulette.prizes_table_partial, name="prizes_table"),
    path("prizes/create/", roulette.prize_create_partial, name="prize_create"),
    path("prizes/<int:prize_id>/edit/", roulette.prize_edit_partial, name="prize_edit"),
    path("prizes/<int:prize_id>/delete/", roulette.prize_delete_partial, name="prize_delete"),
]
