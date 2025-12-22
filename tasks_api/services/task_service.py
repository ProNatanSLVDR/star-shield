"""
Task execution service - wraps services with TaskExecution tracking.
Handles all TaskExecution model interactions.
"""

import logging

from auths.models import Etablissement
from tasks_api.models import TaskExecution
from tasks_api.services.review_service import fetch_stats, fetch_reviews
from django.utils import timezone

logger = logging.getLogger(__name__)


def execute_fetch_all(etablissement_id: int) -> None:
    """
    Execute full review import with task execution tracking.
    Creates a TaskExecution record, calls review_service.fetch_all_reviews(),
    and handles success/error tracking.
    """
    # Create task execution record first (etablissement may not exist)
    task_execution = TaskExecution.objects.create(
        task_type="fetch_reviews_all",
        etablissement=None,  # Will be set after lookup
        status="running",
        metadata={"etablissement_id": etablissement_id},
    )

    try:
        # Get Etablissement - this can fail and will be caught below
        try:
            etablissement = Etablissement.objects.get(id=etablissement_id)
        except Etablissement.DoesNotExist:
            error_msg = f"Etablissement {etablissement_id} not found"
            logger.error(f"[{etablissement_id}] {error_msg}")
            task_execution.mark_error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"[{etablissement_id}] Etablissement: {etablissement}")

        # Update task execution with etablissement reference
        task_execution.etablissement = etablissement
        task_execution.save(update_fields=["etablissement"])

        # Fetch stats first
        fetch_stats(etablissement)

        # Then fetch all reviews
        fetch_reviews(etablissement, new_only=False)

        # Update last_reviews_update timestamp
        etablissement.last_reviews_update = timezone.now()
        etablissement.save(update_fields=["last_reviews_update"])

        # Mark task as successful
        task_execution.mark_success()
    except ValueError as e:
        # ValueError could come from nested Etablissement lookup (already handled)
        # or from fetch_all_reviews() (need to handle)
        # Check if task is still in "running" status - if so, mark as error
        task_execution.refresh_from_db()
        if task_execution.status == "running":
            task_execution.mark_error(str(e))
        logger.error(f"[{etablissement_id}] Error in execute_fetch_all: {e}")
        raise
    except Exception as e:
        # Mark task as failed for any other exception
        task_execution.mark_error(str(e))
        logger.error(f"[{etablissement_id}] Error in execute_fetch_all: {e}")
        raise


def execute_fetch_refresh(etablissement_id: int) -> None:
    """
    Execute incremental review refresh with task execution tracking.
    Creates a TaskExecution record, calls review_service.fetch_new_reviews(),
    and handles success/error tracking.
    """
    # Create task execution record first (etablissement may not exist)
    task_execution = TaskExecution.objects.create(
        task_type="fetch_reviews_refresh",
        etablissement=None,  # Will be set after lookup
        status="running",
        metadata={"etablissement_id": etablissement_id},
    )

    try:
        # Get Etablissement - this can fail and will be caught below
        try:
            etablissement = Etablissement.objects.get(id=etablissement_id)
        except Etablissement.DoesNotExist:
            error_msg = f"Etablissement {etablissement_id} not found"
            logger.error(f"[{etablissement_id}] {error_msg}")
            task_execution.mark_error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"[{etablissement_id}] Etablissement: {etablissement}")

        # Update task execution with etablissement reference
        task_execution.etablissement = etablissement
        task_execution.save(update_fields=["etablissement"])

        # Fetch stats first
        fetch_stats(etablissement)

        # Then fetch new reviews
        fetch_reviews(etablissement, new_only=True)

        # Update last_reviews_update timestamp
        etablissement.last_reviews_update = timezone.now()
        etablissement.save(update_fields=["last_reviews_update"])

        # Mark task as successful
        task_execution.mark_success()
    except ValueError as e:
        # ValueError could come from nested Etablissement lookup (already handled)
        # or from fetch_new_reviews() (need to handle)
        # Check if task is still in "running" status - if so, mark as error
        task_execution.refresh_from_db()
        if task_execution.status == "running":
            task_execution.mark_error(str(e))
        logger.error(f"[{etablissement_id}] Error in execute_fetch_refresh: {e}")
        raise
    except Exception as e:
        # Mark task as failed for any other exception
        task_execution.mark_error(str(e))
        logger.error(f"[{etablissement_id}] Error in execute_fetch_refresh: {e}")
        raise
