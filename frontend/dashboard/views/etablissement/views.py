from django.db.models import Avg
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from auths.models import Etablissement, RatingHistory
from frontend.reviews.models import Review
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from utils.qrcodes import generate_qrcode


@google_gmb_connected_required
@selected_etablissement_required
def overview_view(request):
    etablissement = request.etablissement

    # Get all reviews for this establishment
    all_reviews = Review.objects.filter(etablissement=etablissement)

    # Total reviews count
    total_reviews = all_reviews.count()

    # Average rating
    avg_rating = all_reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    # Positive reviews (rating >= threshold) - these would be redirected to Google
    positive_reviews_count = all_reviews.filter(
        rating__gte=etablissement.review_threshold
    ).count()

    # Private feedback (rating < threshold) - these stay internal
    private_feedback_count = all_reviews.filter(
        rating__lt=etablissement.review_threshold
    ).count()

    # Redirection rate (percentage)
    redirection_rate = (
        (positive_reviews_count / total_reviews * 100) if total_reviews > 0 else 0
    )

    # Recent activity - reviews in last 7 and 30 days
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    recent_7_days = all_reviews.filter(created_at__gte=seven_days_ago).count()
    recent_30_days = all_reviews.filter(created_at__gte=thirty_days_ago).count()

    # Review distribution by rating (1-5 stars)
    review_distribution = {}
    for rating in range(1, 6):
        count = all_reviews.filter(rating=rating).count()
        internal_count = all_reviews.filter(rating=rating, source="internal").count()
        google_count = all_reviews.filter(rating=rating, source="google").count()
        review_distribution[rating] = {
            "total": count,
            "internal": internal_count,
            "google": google_count,
        }

    # Recent reviews (last 10)
    recent_reviews = all_reviews.order_by("-created_at")[:10]

    # Get latest rating history
    latest_rating_history = (
        RatingHistory.objects.filter(etablissement=etablissement)
        .order_by("-created_at")
        .first()
    )

    # Rating trend - compare with previous entry
    rating_trend = None
    if latest_rating_history:
        previous_history = (
            RatingHistory.objects.filter(
                etablissement=etablissement,
                created_at__lt=latest_rating_history.created_at,
            )
            .order_by("-created_at")
            .first()
        )

        if previous_history:
            if latest_rating_history.rating > previous_history.rating:
                rating_trend = "improving"
            elif latest_rating_history.rating < previous_history.rating:
                rating_trend = "declining"
            else:
                rating_trend = "stable"

    # Generate QR code for feedback URL
    identifier = etablissement.slug or str(etablissement.uuid)
    feedback_url = request.build_absolute_uri(
        reverse("reviews:feedback", args=[identifier])
    )
    qr_code_svg = generate_qrcode(feedback_url, size=20)

    context = {
        "etablissement": etablissement,
        "total_reviews": total_reviews,
        "avg_rating": round(avg_rating, 2) if avg_rating else 0,
        "positive_reviews_count": positive_reviews_count,
        "private_feedback_count": private_feedback_count,
        "redirection_rate": round(redirection_rate, 1),
        "recent_7_days": recent_7_days,
        "recent_30_days": recent_30_days,
        "review_distribution": review_distribution,
        "recent_reviews": recent_reviews,
        "latest_rating_history": latest_rating_history,
        "rating_trend": rating_trend,
        "qr_code_svg": qr_code_svg,
        "feedback_url": feedback_url,
    }

    return starshield_render(
        request,
        "etablissement/overview.html",
        context=context,
        page_name="etablissement",
    )
