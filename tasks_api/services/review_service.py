"""
Review fetching service - pure business logic for managing reviews.
No task execution tracking, no API concerns.
"""

import logging

from auths.models import Etablissement, RatingHistory
from frontend.reviews.models import Review
from frontend.reviews.utils import google_stars_to_number

logger = logging.getLogger(__name__)


def fetch_stats(etablissement: Etablissement) -> None:
    """
    Fetch and record rating statistics for an Etablissement.
    Creates a RatingHistory entry with current average rating and total review count.
    """

    reviews_service = etablissement.google_credential.get_reviews_service()
    if reviews_service is None:
        error_msg = f"Unable to initialize reviews service for {etablissement.title}"
        logger.error(f"[{etablissement.id}] {error_msg}")
        raise RuntimeError(error_msg)

    parent_path = f"{etablissement.account_id}/{etablissement.location_id}"

    # Fetch stats
    try:
        stats_response = reviews_service.accounts().locations().reviews().list(parent=parent_path, pageSize=1).execute()
    except Exception as e:
        error_msg = f"Error fetching review stats for {etablissement.title}: {e}"
        logger.error(f"[{etablissement.id}] {error_msg}")
        etablissement.google_credential._check_and_set_invalid_grant(e)
        raise RuntimeError(error_msg) from e

    # Record rating history
    try:
        RatingHistory.objects.create(
            etablissement=etablissement,
            rating=stats_response.get("averageRating", 0),
            total_reviews=stats_response.get("totalReviewCount", 0),
        )
        logger.info(f"[{etablissement.id}] Successfully recorded stats for Etablissement {etablissement}")
    except Exception as e:
        logger.error(f"[{etablissement.id}] Error recording rating history for {etablissement}: {e}")
        raise RuntimeError(f"Error recording rating history: {e}") from e


def fetch_reviews(etablissement: Etablissement, force_import: bool = False) -> None:
    """
    Fetch reviews from Google My Business API.

    Args:
        etablissement_id: The ID of the Etablissement to fetch reviews for
        force_import: If True, import all reviews. If False, stop when finding existing review.
    """

    reviews_service = etablissement.google_credential.get_reviews_service()
    if reviews_service is None:
        error_msg = f"Unable to initialize reviews service for {etablissement.title}"
        logger.error(f"[{etablissement.id}] {error_msg}")
        raise RuntimeError(error_msg)

    logger.info(f"[{etablissement.id}] Starting review import (force_import={force_import})")

    continue_import = True
    import_count = 0
    next_page_token = None

    while continue_import is True:
        try:
            reviews_data = (
                reviews_service.accounts()
                .locations()
                .reviews()
                .list(
                    parent=f"{etablissement.account_id}/{etablissement.location_id}",
                    pageSize=50,
                    pageToken=next_page_token,
                )
                .execute()
            )
        except Exception as e:
            error_msg = f"Error fetching reviews for {etablissement}: {e}"
            logger.error(f"[{etablissement.id}] {error_msg}")
            etablissement.google_credential._check_and_set_invalid_grant(e)
            raise RuntimeError(error_msg) from e

        reviews_list = reviews_data.get("reviews", [])
        if not reviews_list:
            break

        for review in reviews_list:
            try:
                new_review, created = Review.objects.update_or_create(
                    etablissement=etablissement,
                    source="google",
                    google_review_id=review.get("reviewId"),
                    defaults={
                        "comment": review.get("comment", ""),
                        "rating": google_stars_to_number(review.get("starRating")),
                        "google_reviewer_data": review.get("reviewer"),
                        "writen_at": review.get("createTime"),
                    },
                )
                import_count += 1
                logger.debug(f"[{etablissement.id}] Imported review {import_count} for {etablissement}")

                # Stop import if we find an existing review and force_import is False
                if not force_import and not created:
                    continue_import = False
                    logger.info(f"[{etablissement.id}] Found existing review, stopping import for {etablissement}")
                    break
            except Exception as e:
                logger.error(f"[{etablissement.id}] Error creating review: {e}")
                continue

        logger.info(f"[{etablissement.id}] Imported {import_count} reviews")
        # Check if there's a next page
        next_page_token = reviews_data.get("nextPageToken", None)
        if next_page_token is None or not continue_import:
            break

    logger.info(f"[{etablissement.id}] Completed review import: {import_count} reviews processed")
