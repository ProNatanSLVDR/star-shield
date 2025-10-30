"""
URL configuration for tasks_api project.
"""

from django.urls import path
from ninja import NinjaAPI

from tasks_api.api.router import api_router

# Create Django Ninja API instance
api = NinjaAPI(
    title="Tasks API",
    version="1.0.0",
    description="API for managing async review fetching tasks",
)

# Mount the API router
api.add_router("/tasks/reviews", api_router)

urlpatterns = [
    path("api/v1/", api.urls),
]

