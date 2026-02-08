"""
Queue service for enqueuing refresh tasks to Cloud Tasks.
"""

import datetime
import json
from typing import Any

from django.conf import settings
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

from apps.private.auths.models import Etablissement
from starshield.logger import logger


def create_google_cloud_task(
    queue: str,
    url: str,
    payload: dict,
    task_id: str,
    scheduled_seconds_from_now: int = None,
    timeout: int = None,
) -> dict:
    PROJECT_ID = settings.GCP_PROJECT_ID
    LOCATION = settings.GCP_PROJECT_REGION

    # Initialize Cloud Tasks client
    client = tasks_v2.CloudTasksClient()

    task_id_generated = f"{task_id}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Construct the task.
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=url,
            headers={"Content-type": "application/json"},
            body=json.dumps(payload).encode(),
            oidc_token=tasks_v2.OidcToken(service_account_email=settings.CLOUD_TASKS_SERVICE_ACCOUNT),
        ),
        name=(client.task_path(PROJECT_ID, LOCATION, queue, task_id_generated)),
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


def enqueue_full_import_task(etablissement_id: int) -> None:
    """
    Enqueue a full import task for a single etablissement to Cloud Tasks queue.
    This triggers a fetch-all operation that imports all reviews and stats.

    Args:
        etablissement_id: ID of the Etablissement to process

    Returns:
        None (logs errors but doesn't raise)
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    try:
        # Build target URL for fetch-all endpoint
        target_url = f"{base_url.rstrip('/')}/v1/fetch-all"

        # Create task payload
        payload = {"etablissement_id": etablissement_id}

        create_google_cloud_task(
            queue=queue_name,
            url=target_url,
            payload=payload,
            task_id=f"etablissement_{etablissement_id}_full_import",
        )

        logger.info(f"Enqueued full import task for etablissement {etablissement_id}")

    except Exception as e:
        logger.error(f"Failed to enqueue full import task for etablissement {etablissement_id}: {e}", exc_info=True)


def enqueue_refresh_task(etablissement_id: int) -> None:
    """
    Enqueue a refresh task for a single etablissement to Cloud Tasks queue.
    This triggers a fetch-refresh operation that imports only new reviews and stats.

    Args:
        etablissement_id: ID of the Etablissement to process

    Returns:
        None (logs errors but doesn't raise)
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    try:
        # Build target URL for fetch-refresh endpoint
        target_url = f"{base_url.rstrip('/')}/v1/fetch-refresh"

        # Create task payload
        payload = {"etablissement_id": etablissement_id}

        create_google_cloud_task(
            queue=queue_name,
            url=target_url,
            payload=payload,
            task_id=f"etablissement_{etablissement_id}_refresh",
        )

        logger.info(f"Enqueued refresh task for etablissement {etablissement_id}")

    except Exception as e:
        logger.error(f"Failed to enqueue refresh task for etablissement {etablissement_id}: {e}", exc_info=True)


def enqueue_refresh_tasks() -> dict[str, Any]:
    """
    Enqueue refresh tasks for all etablissements to Cloud Tasks queue.

    Returns:
        Dictionary with summary of enqueued tasks:
        - total: Total number of etablissements found
        - enqueued: Number of tasks successfully enqueued
        - failed: Number of tasks that failed to enqueue
        - errors: List of error messages for failed tasks
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

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


def enqueue_ai_responses_task(etablissement_id: int) -> None:
    """
    Enqueue an AI response generation task for a single etablissement.

    Args:
        etablissement_id: ID of the Etablissement to process
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    try:
        target_url = f"{base_url.rstrip('/')}/v1/generate-ai-responses"
        payload = {"etablissement_id": etablissement_id}

        create_google_cloud_task(
            queue=queue_name,
            url=target_url,
            payload=payload,
            task_id=f"etablissement_{etablissement_id}_ai_responses",
        )

        logger.info(f"Enqueued AI responses task for etablissement {etablissement_id}")

    except Exception as e:
        logger.error(f"Failed to enqueue AI responses task for etablissement {etablissement_id}: {e}", exc_info=True)


def enqueue_ai_responses_tasks() -> dict[str, Any]:
    """
    Enqueue AI response tasks for all etablissements with AI responses enabled.

    Returns:
        Dictionary with summary of enqueued tasks.
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    etablissements = Etablissement.objects.filter(active=True, ai_responses_enabled=True)
    total = etablissements.count()

    logger.info(f"Enqueuing AI response tasks for {total} etablissements")

    target_url = f"{base_url.rstrip('/')}/v1/generate-ai-responses"

    enqueued = 0
    failed = 0
    errors = []

    for etablissement in etablissements:
        try:
            payload = {"etablissement_id": etablissement.id}

            create_google_cloud_task(
                queue=queue_name,
                url=target_url,
                payload=payload,
                task_id=f"etablissement_{etablissement.id}_ai_responses",
            )

            enqueued += 1
            logger.info(f"Enqueued AI responses task for etablissement {etablissement.id} ({etablissement.title})")

        except Exception as e:
            failed += 1
            error_msg = f"Failed to enqueue AI responses task for etablissement {etablissement.id}: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    logger.info(f"AI responses enqueueing complete: {enqueued} enqueued, {failed} failed out of {total} total")

    return {
        "total": total,
        "enqueued": enqueued,
        "failed": failed,
        "errors": errors,
    }


def enqueue_weekly_summary_task(etablissement_id: int) -> None:
    """
    Enqueue a weekly summary generation task for a single etablissement.

    Args:
        etablissement_id: ID of the Etablissement to process
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    try:
        target_url = f"{base_url.rstrip('/')}/v1/generate-weekly-summary"
        payload = {"etablissement_id": etablissement_id}

        create_google_cloud_task(
            queue=queue_name,
            url=target_url,
            payload=payload,
            task_id=f"etablissement_{etablissement_id}_weekly_summary",
        )

        logger.info(f"Enqueued weekly summary task for etablissement {etablissement_id}")

    except Exception as e:
        logger.error(f"Failed to enqueue weekly summary task for etablissement {etablissement_id}: {e}", exc_info=True)


def enqueue_weekly_summary_tasks() -> dict[str, Any]:
    """
    Enqueue weekly summary tasks for all etablissements.

    Returns:
        Dictionary with summary of enqueued tasks.
    """
    queue_name = settings.TASKS_API_QUEUE_NAME
    base_url = settings.TASKS_API_BASE_URL

    etablissements = Etablissement.objects.filter(active=True)
    total = etablissements.count()

    logger.info(f"Enqueuing weekly summary tasks for {total} active etablissements")

    target_url = f"{base_url.rstrip('/')}/v1/generate-weekly-summary"

    enqueued = 0
    failed = 0
    errors = []

    for etablissement in etablissements:
        try:
            payload = {"etablissement_id": etablissement.id}

            create_google_cloud_task(
                queue=queue_name,
                url=target_url,
                payload=payload,
                task_id=f"etablissement_{etablissement.id}_weekly_summary",
            )

            enqueued += 1
            logger.info(f"Enqueued weekly summary task for etablissement {etablissement.id} ({etablissement.title})")

        except Exception as e:
            failed += 1
            error_msg = f"Failed to enqueue weekly summary task for etablissement {etablissement.id}: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    logger.info(f"Weekly summary enqueueing complete: {enqueued} enqueued, {failed} failed out of {total} total")

    return {
        "total": total,
        "enqueued": enqueued,
        "failed": failed,
        "errors": errors,
    }
