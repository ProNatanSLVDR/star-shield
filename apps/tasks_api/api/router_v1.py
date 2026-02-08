"""
Django Ninja API router for tasks endpoints.
"""

from ninja import Router
from ninja.errors import HttpError

from apps.tasks_api.api.schemas import (
    AiResponseResult,
    EnqueueRefreshResponse,
    ReviewFetchRequest,
    ReviewFetchResponse,
)
from apps.tasks_api.api.task_tracking import TaskTracker
from apps.tasks_api.services.ai_response_service import generate_and_send_responses
from apps.tasks_api.services.queue_service import (
    enqueue_ai_responses_tasks,
    enqueue_refresh_tasks,
    enqueue_weekly_summary_tasks,
)
from apps.tasks_api.services.review_service import fetch_reviews, fetch_stats
from apps.tasks_api.services.weekly_summary_service import generate_and_store_weekly_summary
from starshield.logger import logger

api_router = Router()


@api_router.post("/fetch-all", response=ReviewFetchResponse)
def fetch_all(request, payload: ReviewFetchRequest):
    """
    Initial/full import handler - fetches stats and all reviews without stopping on existing ones.
    Called by Cloud Tasks.
    """
    try:
        tracker = TaskTracker("fetch_reviews_all", payload.etablissement_id, skip_active_check=True)
        tracker.execute(
            [
                fetch_stats,
                lambda e: fetch_reviews(e, new_only=False),
            ],
        )
        return ReviewFetchResponse(
            etablissement_id=payload.etablissement_id,
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Error processing fetch-all task: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")


@api_router.post("/fetch-refresh", response=ReviewFetchResponse)
def fetch_refresh(request, payload: ReviewFetchRequest):
    """
    Incremental refresh handler - fetches stats and new reviews until it finds an existing one.
    Called by Cloud Tasks for nightly syncs.
    """
    try:
        tracker = TaskTracker("fetch_reviews_refresh", payload.etablissement_id, skip_active_check=True)
        tracker.execute(
            [
                fetch_stats,
                lambda e: fetch_reviews(e, new_only=True),
            ],
        )
        return ReviewFetchResponse(
            etablissement_id=payload.etablissement_id,
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Error processing fetch-refresh task: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")


@api_router.post("/enqueue-refresh-all", response=EnqueueRefreshResponse)
def enqueue_refresh_all(request):
    """
    Enqueue refresh tasks for all etablissements to Cloud Tasks queue.
    Called by Cloud Scheduler to trigger batch refresh of all establishments.
    """
    try:
        result = enqueue_refresh_tasks()
        return EnqueueRefreshResponse(**result)
    except RuntimeError as e:
        logger.error(f"Error enqueueing refresh tasks: {e}")
        raise HttpError(500, str(e))
    except Exception as e:
        logger.error(f"Unexpected error enqueueing refresh tasks: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")


@api_router.post("/generate-ai-responses", response=AiResponseResult)
def generate_ai_responses(request, payload: ReviewFetchRequest):
    """
    Generate and post AI responses for an establishment's unreplied reviews.
    Called by Cloud Tasks.
    """
    try:
        tracker = TaskTracker("generate_ai_responses", payload.etablissement_id)
        result = {}

        def run_ai_responses(etablissement):
            nonlocal result
            result = generate_and_send_responses(etablissement)

        tracker.execute([run_ai_responses])
        return AiResponseResult(
            etablissement_id=payload.etablissement_id,
            **result,
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Error processing AI responses task: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")


@api_router.post("/enqueue-ai-responses-all", response=EnqueueRefreshResponse)
def enqueue_ai_responses_all(request):
    """
    Batch enqueue AI response tasks for all enabled establishments.
    Called by Cloud Scheduler.
    """
    try:
        result = enqueue_ai_responses_tasks()
        return EnqueueRefreshResponse(**result)
    except RuntimeError as e:
        logger.error(f"Error enqueueing AI responses tasks: {e}")
        raise HttpError(500, str(e))
    except Exception as e:
        logger.error(f"Unexpected error enqueueing AI responses tasks: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")


@api_router.post("/generate-weekly-summary", response=ReviewFetchResponse)
def generate_weekly_summary(request, payload: ReviewFetchRequest):
    """
    Generate a weekly performance summary for an establishment.
    Called by Cloud Tasks.
    """
    try:
        tracker = TaskTracker("generate_weekly_summary", payload.etablissement_id)
        tracker.execute([generate_and_store_weekly_summary])
        return ReviewFetchResponse(
            etablissement_id=payload.etablissement_id,
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Error processing weekly summary task: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")


@api_router.post("/enqueue-weekly-summaries-all", response=EnqueueRefreshResponse)
def enqueue_weekly_summaries_all(request):
    """
    Batch enqueue weekly summary tasks for all establishments.
    Called by Cloud Scheduler.
    """
    try:
        result = enqueue_weekly_summary_tasks()
        return EnqueueRefreshResponse(**result)
    except RuntimeError as e:
        logger.error(f"Error enqueueing weekly summary tasks: {e}")
        raise HttpError(500, str(e))
    except Exception as e:
        logger.error(f"Unexpected error enqueueing weekly summary tasks: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")
