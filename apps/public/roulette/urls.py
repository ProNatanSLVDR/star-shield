from django.urls import path

from . import views

app_name = "roulette"

urlpatterns = [
    path("<str:identifier>/", views.roulette_view, name="wheel"),
    path("<str:identifier>/cooldown/", views.roulette_cooldown_view, name="cooldown"),
    path("<str:identifier>/spin/", views.spin_roulette_view, name="spin"),
    path("<str:identifier>/result/", views.roulette_result_view, name="result"),
    path("<str:identifier>/result/<str:prize_code>/", views.roulette_result_view, name="result"),
    path("<str:identifier>/verify/", views.verify_code_view, name="verify"),
    path("<str:identifier>/verify/<str:code>/", views.verify_code_view, name="verify"),
]
