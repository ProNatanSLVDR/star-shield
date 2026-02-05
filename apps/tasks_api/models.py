"""
Models for tasks API.
"""

from django.db import models
from django.utils import timezone


class TaskExecution(models.Model):
    """Model to track task executions and their results."""

    TASK_TYPE_CHOICES = [
        ("fetch_reviews_all", "Fetch Reviews All"),
        ("fetch_reviews_refresh", "Fetch Reviews Refresh"),
        ("fetch_stats", "Fetch Stats"),
        ("fetch_reviews", "Fetch Reviews"),
        ("generate_ai_responses", "Generate AI Responses"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("error", "Error"),
    ]

    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    etablissement = models.ForeignKey(
        "auths.Etablissement",
        on_delete=models.CASCADE,
        related_name="task_executions",
        null=True,
        blank=True,
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["etablissement", "-started_at"]),
        ]

    def __str__(self):
        return f"{self.task_type} for {self.etablissement or 'N/A'} - {self.status}"

    def mark_success(self):
        """Mark task as successfully completed."""
        self.status = "success"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_error(self, error_message: str):
        """Mark task as failed with error message."""
        self.status = "error"
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])

    def mark_running(self):
        """Mark task as running."""
        self.status = "running"
        self.save(update_fields=["status"])
