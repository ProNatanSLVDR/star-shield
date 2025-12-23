"""
Queue service for enqueuing refresh tasks to Cloud Tasks.
"""

import json
import logging
from typing import Dict, Any

from django.conf import settings
from google.cloud import tasks_v2

from auths.models import Etablissement

logger = logging.getLogger(__name__)


def enqueue_refresh_tasks() -> Dict[str, Any]:
    """
    Enqueue refresh tasks for all etablissements to Cloud Tasks queue.

    Returns:
        Dictionary with summary of enqueued tasks:
        - total: Total number of etablissements found
        - enqueued: Number of tasks successfully enqueued
        - failed: Number of tasks that failed to enqueue
        - errors: List of error messages for failed tasks
    """
    project_id = settings.CLOUD_TASKS_PROJECT_ID
    location = settings.CLOUD_TASKS_LOCATION
    queue_name = settings.CLOUD_TASKS_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    # Check if Cloud Tasks is configured
    if not project_id or not location or not queue_name:
        error_msg = "Cloud Tasks not configured. Missing PROJECT_ID, LOCATION, or QUEUE_NAME."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if not base_url:
        error_msg = "TASKS_API_BASE_URL not configured."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Get all etablissements
    etablissements = Etablissement.objects.all()
    total = etablissements.count()

    logger.info(f"Enqueuing refresh tasks for {total} etablissements")

    # Initialize Cloud Tasks client
    try:
        client = tasks_v2.CloudTasksClient()
    except Exception as e:
        error_msg = f"Failed to initialize Cloud Tasks client: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

    # Build queue path
    parent = client.queue_path(project_id, location, queue_name)

    # Build target URL
    target_url = f"{base_url.rstrip('/')}/v1/fetch-refresh"

    # Statistics
    enqueued = 0
    failed = 0
    errors = []

    # Enqueue task for each etablissement
    for etablissement in etablissements:
        try:
            # Create task payload
            payload = json.dumps({"etablissement_id": etablissement.id})

            # Build HTTP request
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": target_url,
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "body": payload.encode(),
                }
            }

            # Create the task
            response = client.create_task(parent=parent, task=task)
            enqueued += 1
            logger.info(
                f"Enqueued refresh task for etablissement {etablissement.id} "
                f"({etablissement.title}): {response.name}"
            )

        except Exception as e:
            failed += 1
            error_msg = f"Failed to enqueue task for etablissement {etablissement.id}: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    logger.info(
        f"Enqueueing complete: {enqueued} enqueued, {failed} failed out of {total} total"
    )

    return {
        "total": total,
        "enqueued": enqueued,
        "failed": failed,
        "errors": errors,
    }

