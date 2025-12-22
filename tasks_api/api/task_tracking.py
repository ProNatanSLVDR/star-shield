"""
Task tracking utility - reusable class for tracking task executions.
Handles TaskExecution creation, Etablissement lookup, function execution,
and error tracking.
"""

import logging
from typing import Callable, List, Optional, Dict, Any

from auths.models import Etablissement
from tasks_api.models import TaskExecution
from django.utils import timezone

logger = logging.getLogger(__name__)


class TaskTracker:
    """
    Reusable class for tracking task executions.
    Handles TaskExecution lifecycle, Etablissement lookup, function execution,
    and comprehensive error handling.
    """

    def __init__(
        self,
        task_type: str,
        etablissement_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize task tracker.

        Args:
            task_type: Type of task (must match TaskExecution.TASK_TYPE_CHOICES)
            etablissement_id: ID of the Etablissement to process
            metadata: Optional metadata dictionary to store in TaskExecution
        """
        self.task_type = task_type
        self.etablissement_id = etablissement_id
        self.metadata = metadata or {}
        self.metadata["etablissement_id"] = etablissement_id
        self.task_execution: Optional[TaskExecution] = None
        self.etablissement: Optional[Etablissement] = None

    def execute(
        self,
        task_functions: List[Callable[[Etablissement], None]],
        update_last_reviews: bool = False,
    ) -> None:
        """
        Execute a list of functions with full task tracking.

        Args:
            task_functions: List of callable functions that accept Etablissement as argument
            update_last_reviews: If True, update etablissement.last_reviews_update timestamp

        Raises:
            ValueError: If Etablissement not found
            Exception: Any exception raised by task functions (after tracking)
        """
        # Create task execution record first (etablissement may not exist)
        self.task_execution = TaskExecution.objects.create(
            task_type=self.task_type,
            etablissement=None,  # Will be set after lookup
            status="running",
            metadata=self.metadata,
        )

        try:
            # Get Etablissement - this can fail and will be caught below
            try:
                self.etablissement = Etablissement.objects.get(id=self.etablissement_id)
            except Etablissement.DoesNotExist:
                error_msg = f"Etablissement {self.etablissement_id} not found"
                logger.error(f"[{self.etablissement_id}] {error_msg}")
                self.task_execution.mark_error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"[{self.etablissement_id}] Etablissement: {self.etablissement}")

            # Update task execution with etablissement reference
            self.task_execution.etablissement = self.etablissement
            self.task_execution.save(update_fields=["etablissement"])

            # Execute each function in the list
            for task_func in task_functions:
                task_func(self.etablissement)

            # Optionally update last_reviews_update timestamp
            if update_last_reviews:
                self.etablissement.last_reviews_update = timezone.now()
                self.etablissement.save(update_fields=["last_reviews_update"])

            # Mark task as successful
            self.task_execution.mark_success()

        except ValueError as e:
            # ValueError could come from Etablissement lookup (already handled)
            # or from task functions (need to handle)
            # Check if task is still in "running" status - if so, mark as error
            self.task_execution.refresh_from_db()
            if self.task_execution.status == "running":
                self.task_execution.mark_error(str(e))
            logger.error(f"[{self.etablissement_id}] Error in TaskTracker.execute: {e}")
            raise
        except Exception as e:
            # Mark task as failed for any other exception
            self.task_execution.mark_error(str(e))
            logger.error(f"[{self.etablissement_id}] Error in TaskTracker.execute: {e}")
            raise
