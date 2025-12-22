"""
Django Ninja API router for tasks endpoints.
"""

import logging
from ninja import Router
from ninja.errors import HttpError
from django.conf import settings

from tasks_api.api.task_tracking import TaskTracker
from tasks_api.services.review_service import fetch_stats, fetch_reviews
from tasks_api.services.queue_service import enqueue_refresh_tasks
from tasks_api.api.schemas import (
    ReviewFetchRequest,
    ReviewFetchResponse,
    EnqueueRefreshResponse,
)


logger = logging.getLogger(__name__)

api_router = Router()


def verify_cloud_tasks_auth(request):
    """
    Verify that the request is from Cloud Tasks by checking the Authorization header.
    """
    auth_token = settings.TASKS_API_AUTH_TOKEN
    if not auth_token:
        # If no token is configured, skip auth (development only)
        return True

    auth_header = request.headers.get("Authorization", "")
    expected_header = f"Bearer {auth_token}"

    if auth_header != expected_header:
        logger.warning(f"Invalid auth token in request from {request.META.get('REMOTE_ADDR')}")
        return False

    return True


@api_router.post("/fetch-all", response=ReviewFetchResponse)
def fetch_all(request, payload: ReviewFetchRequest):
    """
    Initial/full import handler - fetches stats and all reviews without stopping on existing ones.
    Called by Cloud Tasks.
    """
    if not verify_cloud_tasks_auth(request):
        raise HttpError(401, "Unauthorized")

    try:
        tracker = TaskTracker("fetch_reviews_all", payload.etablissement_id)
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
    if not verify_cloud_tasks_auth(request):
        raise HttpError(401, "Unauthorized")

    try:
        tracker = TaskTracker("fetch_reviews_refresh", payload.etablissement_id)
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
    if not verify_cloud_tasks_auth(request):
        raise HttpError(401, "Unauthorized")

    try:
        result = enqueue_refresh_tasks()
        return EnqueueRefreshResponse(**result)
    except RuntimeError as e:
        logger.error(f"Error enqueueing refresh tasks: {e}")
        raise HttpError(500, str(e))
    except Exception as e:
        logger.error(f"Unexpected error enqueueing refresh tasks: {e}", exc_info=True)
        raise HttpError(500, "Internal server error")
