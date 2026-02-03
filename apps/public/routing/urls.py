from django.urls import path

from . import views

app_name = "routing"

urlpatterns = [
    path("qr/<str:identifier>/<str:short_code>/", views.qr_code_redirect_view, name="qr_code_redirect"),
    path("inactive/", views.feature_inactive_view, name="feature_inactive"),
]
