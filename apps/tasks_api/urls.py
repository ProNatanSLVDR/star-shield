"""
URL configuration for tasks_api project.
"""

from django.http import JsonResponse
from django.urls import path
from ninja import NinjaAPI

from apps.tasks_api.api.router_v1 import api_router as api_router_v1

# Create Django Ninja API instance
api_v1 = NinjaAPI(
    title="Tasks API",
    version="1.0.0",
    description="API for managing review fetching tasks",
)

# Mount the API router
api_v1.add_router("", api_router_v1)

urlpatterns = [
    path("v1/", api_v1.urls),
]


def api_404(request, exception):
    return JsonResponse({"error": "Not found"}, status=404)


def api_500(request):
    return JsonResponse({"error": "Internal server error"}, status=500)


handler404 = api_404
handler500 = api_500
