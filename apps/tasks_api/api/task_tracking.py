"""
Task tracking utility - reusable class for tracking task executions.
Handles TaskExecution creation, Etablissement lookup, function execution,
and error tracking.
"""

from collections.abc import Callable
from typing import Any

from apps.private.auths.models import Etablissement
from apps.tasks_api.models import TaskExecution
from starshield.logger import logger


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
        metadata: dict[str, Any] | None = None,
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
        self.task_execution: TaskExecution | None = None
        self.etablissement: Etablissement | None = None

    def execute(
        self,
        task_functions: list[Callable[[Etablissement], None]],
    ) -> None:
        """
        Execute a list of functions with full task tracking.

        Args:
            task_functions: List of callable functions that accept Etablissement as argument

        Raises:
            ValueError: If Etablissement not found
            Exception: Any exception raised by task functions (after tracking)
        """

        try:
            # Get Etablissement - this can fail and will be caught below
            try:
                self.etablissement = Etablissement.objects.get(id=self.etablissement_id)
            except Etablissement.DoesNotExist:
                error_msg = f"Etablissement {self.etablissement_id} not found"
                logger.error(f"[{self.etablissement_id}] {error_msg}")
                raise ValueError(error_msg)

            if not self.etablissement.active:
                logger.info(f"[{self.etablissement_id}] Skipping task — etablissement is deactivated")
                return

            logger.info(f"[{self.etablissement_id}] Etablissement: {self.etablissement}")

            self.task_execution = TaskExecution.objects.create(
                task_type=self.task_type,
                etablissement=self.etablissement,
                status="running",
                metadata=self.metadata,
            )

            # Execute each function in the list
            for task_func in task_functions:
                task_func(self.etablissement)

            # Mark task as successful
            self.task_execution.mark_success()

        except ValueError as e:
            if self.task_execution:
                self.task_execution.refresh_from_db()
                if self.task_execution.status == "running":
                    self.task_execution.mark_error(str(e))
            logger.error(f"[{self.etablissement_id}] Error in TaskTracker.execute: {e}")
            raise
        except Exception as e:
            if self.task_execution:
                self.task_execution.mark_error(str(e))
            logger.error(f"[{self.etablissement_id}] Error in TaskTracker.execute: {e}")
            raise
