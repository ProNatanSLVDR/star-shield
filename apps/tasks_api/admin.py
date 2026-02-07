from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.tasks_api.models import TaskExecution


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
    readonly_fields = ("started_at", "completed_at", "metadata", "error_message")
    date_hierarchy = "started_at"

    fieldsets = (
        (
            _("Task"),
            {"fields": ("task_type", "etablissement", "status")},
        ),
        (
            _("Execution Details"),
            {"fields": ("metadata", "error_message")},
        ),
        (
            _("Timing"),
            {"fields": ("started_at", "completed_at")},
        ),
    )
