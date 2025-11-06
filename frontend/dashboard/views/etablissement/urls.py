from django.urls import path, include
from . import views

app_name = "etablissement"

urlpatterns = [
    path('', views.overview_view, name='overview'),
    path('settings/', include(('frontend.dashboard.views.etablissement.settings.urls', 'settings'))),
]
