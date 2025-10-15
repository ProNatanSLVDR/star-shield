from django.urls import path
from .views import feedback_thanks_view, feedback_view

app_name = "reviews"

urlpatterns = [
    path('feedback/<str:identifier>/', feedback_view, name='feedback'),
    path('feedback/<str:identifier>/thanks/', feedback_thanks_view, name='feedback_thanks'),
]
