"""
URL configuration for tasks_api project.
"""

from django.urls import path
from ninja import NinjaAPI

from tasks_api.api.router_v1 import api_router as api_router_v1
from tasks_api.api.auth import BearerTokenAuth

# Create Django Ninja API instance
api = NinjaAPI(
    title="Tasks API",
    version="1.0.0",
    description="API for managing async review fetching tasks",
    auth=BearerTokenAuth(),
)

# Mount the API router
api.add_router("v1/", api_router_v1)

urlpatterns = [
    path("", api.urls),
]
