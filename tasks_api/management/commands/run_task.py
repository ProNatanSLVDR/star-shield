"""
Django management command to run tasks locally, mimicking GCP Cloud Tasks execution.

This command executes tasks directly without enqueueing them to Cloud Tasks,
useful for local development and testing.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from tasks_api.services.task_service import execute_fetch_all, execute_fetch_refresh

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run a task locally (fetch-all or fetch-refresh) for a given Etablissement"

    def add_arguments(self, parser):
        parser.add_argument(
            "task_type",
            type=str,
            help="Task type: 'fetch-all' or 'fetch-refresh'",
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

        # Validate task type
        if task_type not in ["fetch-all", "fetch-refresh"]:
            raise CommandError(f"Invalid task_type: '{task_type}'. Must be 'fetch-all' or 'fetch-refresh'")

        # Execute the appropriate task
        try:
            if task_type == "fetch-all":
                execute_fetch_all(etablissement_id)
            elif task_type == "fetch-refresh":
                execute_fetch_refresh(etablissement_id)
        except ValueError as e:
            logger.error(f"[{etablissement_id}] Task execution failed: {e}")
            raise CommandError(f"Task execution failed: {e}") from e
        except Exception as e:
            logger.error(f"[{etablissement_id}] Unexpected error during task execution: {e}")
            raise CommandError(f"Unexpected error during task execution: {e}") from e

        logger.info(f"[{etablissement_id}] Task execution completed: {task_type}")
