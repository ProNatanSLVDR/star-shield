"""
Django Ninja API router for tasks endpoints.
"""

import logging
from ninja import Router
from django.conf import settings

from tasks_api.handlers.review_handler import fetch_reviews_all, fetch_reviews_refresh
from tasks_api.api.schemas import ReviewFetchRequest, ReviewFetchResponse

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
        logger.warning(
            f"Invalid auth token in request from {request.META.get('REMOTE_ADDR')}"
        )
        return False

    return True


@api_router.post("/fetch-all", response=ReviewFetchResponse)
def fetch_all(request, payload: ReviewFetchRequest):
    """
    Initial/full import handler - fetches stats and all reviews without stopping on existing ones.
    Called by Cloud Tasks.
    """
    if not verify_cloud_tasks_auth(request):
        return ReviewFetchResponse(
            status="error",
            etablissement_id=payload.etablissement_id,
            message="Unauthorized",
        ), 401

    try:
        fetch_reviews_all(payload.etablissement_id)
        return ReviewFetchResponse(
            status="success",
            etablissement_id=payload.etablissement_id,
            message="Full import completed",
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return ReviewFetchResponse(
            status="error", etablissement_id=payload.etablissement_id, message=str(e)
        ), 400
    except Exception as e:
        logger.error(f"Error processing fetch-all task: {e}", exc_info=True)
        return ReviewFetchResponse(
            status="error", etablissement_id=payload.etablissement_id, message=str(e)
        ), 500


@api_router.post("/fetch-refresh", response=ReviewFetchResponse)
def fetch_refresh(request, payload: ReviewFetchRequest):
    """
    Incremental refresh handler - fetches stats and new reviews until it finds an existing one.
    Called by Cloud Tasks for nightly syncs.
    """
    if not verify_cloud_tasks_auth(request):
        return ReviewFetchResponse(
            status="error",
            etablissement_id=payload.etablissement_id,
            message="Unauthorized",
        ), 401

    try:
        fetch_reviews_refresh(payload.etablissement_id)
        return ReviewFetchResponse(
            status="success",
            etablissement_id=payload.etablissement_id,
            message="Refresh import completed",
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return ReviewFetchResponse(
            status="error", etablissement_id=payload.etablissement_id, message=str(e)
        ), 400
    except Exception as e:
        logger.error(f"Error processing fetch-refresh task: {e}", exc_info=True)
        return ReviewFetchResponse(
            status="error", etablissement_id=payload.etablissement_id, message=str(e)
        ), 500
