"""
Admin configuration for tasks_api app.
"""

from django.contrib import admin

from tasks_api.models import TaskExecution


@admin.register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "task_type",
        "etablissement",
        "status",
        "started_at",
        "completed_at",
    )
    list_filter = ("task_type", "status", "started_at")
    search_fields = ("etablissement__title", "error_message")
    readonly_fields = ("started_at", "completed_at")
    date_hierarchy = "started_at"
