"""
Review fetching service - pure business logic for managing reviews.
No task execution tracking, no API concerns.
"""

import logging

from apps.private.auths.models import Etablissement, RatingHistory
from apps.public.reviews.models import Review
from apps.public.reviews.utils import google_stars_to_number

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
        logger.info(f"[{etablissement.id}] Etablissement stats recorded")
    except Exception as e:
        logger.error(f"[{etablissement.id}] Error recording rating history for {etablissement}: {e}")
        raise RuntimeError(f"Error recording rating history: {e}") from e


def fetch_reviews(etablissement: Etablissement, new_only: bool = False) -> None:
    """
    Fetch reviews from Google My Business API.

    Args:
        etablissement_id: The ID of the Etablissement to fetch reviews for
        new_only: If True, import only new reviews. If False, import all reviews.
    """

    reviews_service = etablissement.google_credential.get_reviews_service()
    if reviews_service is None:
        error_msg = f"Unable to initialize reviews service for {etablissement.title}"
        logger.error(f"[{etablissement.id}] {error_msg}")
        raise RuntimeError(error_msg)

    logger.info(f"[{etablissement.id}] Starting review import (new_only={new_only})")

    # Import loop
    continue_import = True
    import_count = 0
    next_page_token = None
    consecutive_existing_count = 0

    # Import stats
    page_number = 0
    total_new_count = 0
    total_existing_count = 0
    # Threshold: stop if we've seen a full page (50) of consecutive existing reviews
    # This handles gaps in the database while ensuring we don't process all reviews unnecessarily
    EXISTING_REVIEW_THRESHOLD = 50

    while continue_import is True:
        page_number += 1
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

        # Track how many reviews in this page were existing vs new
        page_new_count = 0
        page_existing_count = 0

        # Process all reviews in the current page
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
                review_id = review.get("reviewId", "unknown")
                status = "new" if created else "existing"
                logger.debug(f"[{etablissement.id}] Review {import_count} ({status}): {review_id}")

                if created:
                    page_new_count += 1
                    # Reset consecutive existing count when we find a new review
                    consecutive_existing_count = 0
                else:
                    page_existing_count += 1
                    if new_only:
                        consecutive_existing_count += 1
            except Exception as e:
                logger.error(f"[{etablissement.id}] Error creating review: {e}")
                continue

        total_new_count += page_new_count
        total_existing_count += page_existing_count

        logger.info(
            f"[{etablissement.id}] Page {page_number} processed: {page_new_count} new, {page_existing_count} existing"
        )
        # For new_only mode: stop if we've encountered enough consecutive existing reviews
        # This ensures we don't miss newer reviews due to gaps in the database
        if new_only and consecutive_existing_count >= EXISTING_REVIEW_THRESHOLD:
            continue_import = False
            logger.info(
                f"[{etablissement.id}] {consecutive_existing_count} consecutive existing reviews, stopping import"
            )
            break

        # Check if there's a next page
        next_page_token = reviews_data.get("nextPageToken", None)
        if next_page_token is None or not continue_import:
            break

    logger.info(
        f"[{etablissement.id}] Completed review import: {total_new_count} new, {total_existing_count} existing reviews across {page_number} pages"
    )
