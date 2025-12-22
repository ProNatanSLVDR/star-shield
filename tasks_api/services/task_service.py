"""
Task execution service - wraps services with TaskExecution tracking.
Handles all TaskExecution model interactions.
"""

from tasks_api.api.task_tracking import TaskTracker
from tasks_api.services.review_service import fetch_stats, fetch_reviews


def execute_fetch_all(etablissement_id: int) -> None:
    """
    Execute full review import with task execution tracking.
    Creates a TaskExecution record, calls review_service.fetch_all_reviews(),
    and handles success/error tracking.
    """
    tracker = TaskTracker("fetch_reviews_all", etablissement_id)
    tracker.execute(
        [
            fetch_stats,
            lambda e: fetch_reviews(e, new_only=False),
        ],
        update_last_reviews=True,
    )


def execute_fetch_refresh(etablissement_id: int) -> None:
    """
    Execute incremental review refresh with task execution tracking.
    Creates a TaskExecution record, calls review_service.fetch_new_reviews(),
    and handles success/error tracking.
    """
    tracker = TaskTracker("fetch_reviews_refresh", etablissement_id)
    tracker.execute(
        [
            fetch_stats,
            lambda e: fetch_reviews(e, new_only=True),
        ],
        update_last_reviews=True,
    )
