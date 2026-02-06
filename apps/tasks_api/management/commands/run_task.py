"""
Django management command to run tasks locally, mimicking GCP Cloud Tasks execution.

This command executes tasks directly without enqueueing them to Cloud Tasks,
useful for local development and testing.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.tasks_api.api.task_tracking import TaskTracker
from apps.tasks_api.services.ai_response_service import generate_and_send_responses
from apps.tasks_api.services.review_service import fetch_reviews, fetch_stats
from apps.tasks_api.services.weekly_summary_service import generate_and_store_weekly_summary
from starshield.logger import logger


class Command(BaseCommand):
    help = "Run a task locally for a given Etablissement"

    def add_arguments(self, parser):
        parser.add_argument(
            "task_type",
            type=str,
            help="Task type: 'fetch-all', 'fetch-refresh', 'generate-ai-responses', or 'generate-weekly-summary'",
        )
        parser.add_argument(
            "etablissement_id",
            type=int,
            help="ID of the Etablissement to process",
        )

    def handle(self, *args, **options):
        task_type = options["task_type"]
        etablissement_id = options["etablissement_id"]

        logger.info(f"[{etablissement_id}] Starting task execution: {task_type}")

        valid_types = ["fetch-all", "fetch-refresh", "generate-ai-responses", "generate-weekly-summary"]
        if task_type not in valid_types:
            raise CommandError(f"Invalid task_type: '{task_type}'. Must be one of: {', '.join(valid_types)}")

        # Map command task types to TaskTracker task types
        tracker_task_type = {
            "fetch-all": "fetch_reviews_all",
            "fetch-refresh": "fetch_reviews_refresh",
            "generate-ai-responses": "generate_ai_responses",
            "generate-weekly-summary": "generate_weekly_summary",
        }[task_type]

        # Execute the appropriate task using TaskTracker
        try:
            tracker = TaskTracker(tracker_task_type, etablissement_id)
            if task_type == "fetch-all":
                tracker.execute(
                    [
                        fetch_stats,
                        lambda e: fetch_reviews(e, new_only=False),
                    ],
                )
            elif task_type == "fetch-refresh":
                tracker.execute(
                    [
                        fetch_stats,
                        lambda e: fetch_reviews(e, new_only=True),
                    ],
                )
            elif task_type == "generate-ai-responses":
                tracker.execute(
                    [generate_and_send_responses],
                )
            elif task_type == "generate-weekly-summary":
                tracker.execute(
                    [generate_and_store_weekly_summary],
                )
        except ValueError as e:
            logger.error(f"[{etablissement_id}] Task execution failed: {e}")
            raise CommandError(f"Task execution failed: {e}") from e
        except Exception as e:
            logger.error(f"[{etablissement_id}] Unexpected error during task execution: {e}")
            raise CommandError(f"Unexpected error during task execution: {e}") from e

        logger.info(f"[{etablissement_id}] Task execution completed: {task_type}")
