"""
Queue service for enqueuing refresh tasks to Cloud Tasks.
"""

import json
import logging
from typing import Dict, Any

from django.conf import settings
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2
import datetime

from auths.models import Etablissement

logger = logging.getLogger(__name__)


def create_google_cloud_task(
    queue: str,
    url: str,
    payload: dict,
    task_id: str,
    scheduled_seconds_from_now: int = None,
    timeout: int = None,
) -> dict:
    PROJECT_ID = settings.CLOUD_TASKS_PROJECT_ID
    LOCATION = settings.CLOUD_TASKS_LOCATION

    # Initialize Cloud Tasks client
    client = tasks_v2.CloudTasksClient()

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=url,
            headers={"Content-type": "application/json"},
            body=json.dumps(payload).encode(),
            oidc_token=tasks_v2.OidcToken(service_account_email=settings.CLOUD_TASKS_SERVICE_ACCOUNT),
        ),
        name=(client.task_path(PROJECT_ID, LOCATION, queue, task_id)),
    )

    # Convert "seconds from now" to an absolute Protobuf Timestamp
    if scheduled_seconds_from_now is not None:
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(datetime.datetime.utcnow() + datetime.timedelta(seconds=scheduled_seconds_from_now))
        task.schedule_time = timestamp

    # Convert "deadline in seconds" to a Protobuf Duration
    if timeout is not None:
        duration = duration_pb2.Duration()
        duration.FromSeconds(timeout)
        task.dispatch_deadline = duration

    # Create the task
    client.create_task(
        tasks_v2.CreateTaskRequest(
            parent=client.queue_path(PROJECT_ID, LOCATION, queue),
            task=task,
        )
    )


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
    queue_name = settings.TASKS_API_QUEUE_NAME
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

    # Build target URL using revers
    target_url = f"{base_url.rstrip('/')}/v1/fetch-refresh"

    # Statistics
    enqueued = 0
    failed = 0
    errors = []

    # Enqueue task for each etablissement
    for etablissement in etablissements:
        try:
            # Create task payload
            payload = {"etablissement_id": etablissement.id}

            create_google_cloud_task(
                queue=queue_name,
                url=target_url,
                payload=payload,
                task_id=f"etablissement_{etablissement.id}",
                scheduled_seconds_from_now=0,
                timeout=settings.TASK_TIMEOUT_SECONDS,
            )

            enqueued += 1
            logger.info(f"Enqueued refresh task for etablissement {etablissement.id} ({etablissement.title})")

        except Exception as e:
            failed += 1
            error_msg = f"Failed to enqueue task for etablissement {etablissement.id}: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    logger.info(f"Enqueueing complete: {enqueued} enqueued, {failed} failed out of {total} total")

    return {
        "total": total,
        "enqueued": enqueued,
        "failed": failed,
        "errors": errors,
    }
