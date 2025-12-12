"""
Review fetching service - pure business logic for managing reviews.
No task execution tracking, no API concerns.
"""

import logging
from django.utils import timezone

from auths.models import Etablissement, RatingHistory
from frontend.reviews.models import Review
from frontend.reviews.utils import google_stars_to_number

logger = logging.getLogger(__name__)


def fetch_stats(etablissement_id: int) -> None:
    """
    Fetch and record rating statistics for an Etablissement.
    Creates a RatingHistory entry with current average rating and total review count.
    """
    try:
        etablissement = Etablissement.objects.get(id=etablissement_id)
    except Etablissement.DoesNotExist:
        logger.error(f"Etablissement {etablissement_id} not found")
        raise ValueError(f"Etablissement {etablissement_id} not found")

    reviews_service = etablissement.google_credential.get_reviews_service()
    if reviews_service is None:
        error_msg = f"Unable to initialize reviews service for {etablissement.title}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    parent_path = f"{etablissement.account_id}/{etablissement.location_id}"

    # Fetch stats
    try:
        stats_response = reviews_service.accounts().locations().reviews().list(parent=parent_path, pageSize=1).execute()
    except Exception as e:
        error_msg = f"Error fetching review stats for {etablissement.title}: {e}"
        logger.error(error_msg)
        etablissement.google_credential._check_and_set_invalid_grant(e)
        raise RuntimeError(error_msg) from e

    # Record rating history
    try:
        RatingHistory.objects.create(
            etablissement=etablissement,
            rating=stats_response.get("averageRating", 0),
            total_reviews=stats_response.get("totalReviewCount", 0),
        )
        logger.info(f"Successfully recorded stats for Etablissement {etablissement_id}")
    except Exception as e:
        logger.error(f"Error recording rating history for {etablissement.title}: {e}")
        raise RuntimeError(f"Error recording rating history: {e}") from e


def fetch_reviews(etablissement_id: int, force_import: bool = False) -> None:
    """
    Fetch reviews from Google My Business API.

    Args:
        etablissement_id: The ID of the Etablissement to fetch reviews for
        force_import: If True, import all reviews. If False, stop when finding existing review.
    """
    try:
        etablissement = Etablissement.objects.get(id=etablissement_id)
    except Etablissement.DoesNotExist:
        logger.error(f"Etablissement {etablissement_id} not found")
        raise ValueError(f"Etablissement {etablissement_id} not found")

    reviews_service = etablissement.google_credential.get_reviews_service()
    if reviews_service is None:
        error_msg = f"Unable to initialize reviews service for {etablissement.title}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(f"Starting review import for {etablissement.title} (force_import={force_import})")

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
            error_msg = f"Error fetching reviews for {etablissement.title}: {e}"
            logger.error(error_msg)
            etablissement.google_credential._check_and_set_invalid_grant(e)
            raise RuntimeError(error_msg) from e

        location_reviews = reviews_data.get("locationReviews", [])
        if not location_reviews:
            break

        for location_review in location_reviews:
            review = location_review.get("review")
            if review is None:
                continue

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
                logger.debug(f"Imported review {import_count} for {etablissement.title}")

                # Stop import if we find an existing review and force_import is False
                if not force_import and not created:
                    continue_import = False
                    logger.info(f"Found existing review, stopping import for {etablissement.title}")
                    break
            except Exception as e:
                logger.error(f"Error creating review: {e}")
                continue

        # Check if there's a next page
        next_page_token = reviews_data.get("nextPageToken", None)
        if next_page_token is None or not continue_import:
            break

    logger.info(f"Completed review import for {etablissement.title}: {import_count} reviews processed")


def fetch_all_reviews(etablissement_id: int) -> None:
    """
    Full import - fetches stats and all reviews without stopping on existing ones.
    Uses force_import=True to import everything.
    Updates last_reviews_update timestamp on the Etablissement.
    """
    etablissement = Etablissement.objects.get(id=etablissement_id)

    # Fetch stats first
    fetch_stats(etablissement_id)

    # Then fetch all reviews
    fetch_reviews(etablissement_id, force_import=True)

    # Update last_reviews_update timestamp
    etablissement.last_reviews_update = timezone.now()
    etablissement.save(update_fields=["last_reviews_update"])

    logger.info(f"Successfully completed full import for Etablissement {etablissement_id}")


def fetch_new_reviews(etablissement_id: int) -> None:
    """
    Incremental import - fetches stats and new reviews until it finds an existing one.
    Uses force_import=False to stop when encountering existing reviews.
    Updates last_reviews_update timestamp on the Etablissement.
    """
    etablissement = Etablissement.objects.get(id=etablissement_id)

    # Fetch stats first
    fetch_stats(etablissement_id)

    # Then fetch new reviews
    fetch_reviews(etablissement_id, force_import=False)

    # Update last_reviews_update timestamp
    etablissement.last_reviews_update = timezone.now()
    etablissement.save(update_fields=["last_reviews_update"])

    logger.info(f"Successfully completed refresh import for Etablissement {etablissement_id}")
