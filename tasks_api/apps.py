"""
App configuration for tasks_api.
"""

from django.apps import AppConfig


class TasksApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks_api"
    verbose_name = "Tasks API"
