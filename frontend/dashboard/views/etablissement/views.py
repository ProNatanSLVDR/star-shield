from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta
import json
from frontend.reviews.models import Review, ReviewAnalytics
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)


@google_gmb_connected_required
@selected_etablissement_required
def overview_view(request):
    etablissement = request.etablissement

    rating_history_qs = etablissement.rating_history.order_by("created_at")

    rating_history_points: list[dict] = []
    for entry in rating_history_qs:
        rating_history_points.append(
            {
                "date": entry.created_at.strftime("%Y-%m-%d"),
                "label": entry.created_at.strftime("%d %b %Y"),
                "rating": float(entry.rating),
                "total_reviews": entry.total_reviews,
            }
        )

    current_rating = (
        rating_history_points[-1]["rating"] if rating_history_points else None
    )
    current_reviews_total = (
        rating_history_points[-1]["total_reviews"] if rating_history_points else 0
    )

    last_rating_update = None
    if rating_history_points:
        last_rating_update = rating_history_qs.last().created_at

    goal_rating = None
    if etablissement.target_rating is not None:
        goal_rating = float(etablissement.target_rating)

    goal_projection_points: list[dict] = []
    if goal_rating is not None:
        origin_date = last_rating_update or timezone.now()

        start_rating = goal_rating
        if current_rating is not None and rating_history_points:
            origin_date = rating_history_qs.last().created_at
            start_rating = current_rating

        projected_goal_date = origin_date + timedelta(days=30 * 6)

        goal_projection_points = [
            {
                "date": origin_date.strftime("%Y-%m-%d"),
                "rating": float(start_rating),
            },
            {
                "date": projected_goal_date.strftime("%Y-%m-%d"),
                "rating": goal_rating,
            },
        ]

    reviews_queryset = Review.objects.filter(etablissement=etablissement)

    average_rating = reviews_queryset.aggregate(avg=Avg("rating"))["avg"]
    if average_rating is not None:
        average_rating = float(average_rating)

    total_reviews = reviews_queryset.count()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_reviews_count = reviews_queryset.filter(
        created_at__gte=thirty_days_ago
    ).count()

    rating_change = None
    if len(rating_history_points) >= 2:
        latest_rating = rating_history_points[-1]["rating"]
        previous_rating = rating_history_points[-2]["rating"]
        rating_change = round(latest_rating - previous_rating, 2)

    goal_gap = None
    goal_gap_abs = None
    if goal_rating is not None and current_rating is not None:
        goal_gap = round(goal_rating - current_rating, 2)
    if goal_gap is not None:
        goal_gap_abs = abs(goal_gap)

    source_breakdown = {
        row["source"]: row["total"]
        for row in reviews_queryset.values("source").annotate(total=Count("id"))
    }

    google_reviews_count = source_breakdown.get("google", 0)
    internal_reviews_count = source_breakdown.get("internal", 0)
    other_reviews_count = total_reviews - google_reviews_count - internal_reviews_count
    if other_reviews_count < 0:
        other_reviews_count = 0

    rating_distribution_raw = {
        row["rating"]: row["total"]
        for row in reviews_queryset.values("rating").annotate(total=Count("id"))
    }
    rating_distribution = []
    for star in range(5, 0, -1):
        rating_distribution.append(
            {
                "rating": star,
                "count": rating_distribution_raw.get(star, 0),
            }
        )

    positive_reviews_percentage = None
    if total_reviews > 0:
        positive_reviews_count = reviews_queryset.filter(rating__gte=4).count()
        positive_reviews_percentage = round(
            (positive_reviews_count / total_reviews) * 100,
            1,
        )

    # Analytics stats from ReviewAnalytics
    analytics_queryset = ReviewAnalytics.objects.filter(etablissement=etablissement)
    qr_page_visits = analytics_queryset.filter(type="review_page_consulted").count()
    reviews_redirected_google = analytics_queryset.filter(
        type="external_feedback"
    ).count()
    reviews_kept_private = analytics_queryset.filter(type="internal_feedback").count()

    # Conversion rate: percentage of QR visits that resulted in reviews
    conversion_rate = None
    if qr_page_visits > 0:
        conversion_rate = round((total_reviews / qr_page_visits) * 100, 1)

    # Last review update time
    last_review_update = None
    last_review = reviews_queryset.order_by("-created_at").first()
    if last_review:
        last_review_update = last_review.created_at

    chart_payload = {
        "history": rating_history_points,
        "goal": goal_projection_points,
    }

    context = {
        "etablissement": etablissement,
        "chart_payload_json": json.dumps(chart_payload),
        "current_rating": current_rating,
        "current_reviews_total": current_reviews_total,
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "recent_reviews_count": recent_reviews_count,
        "rating_change": rating_change,
        "goal_rating": goal_rating,
        "goal_gap": goal_gap,
        "goal_gap_abs": goal_gap_abs,
        "source_breakdown": source_breakdown,
        "google_reviews_count": google_reviews_count,
        "internal_reviews_count": internal_reviews_count,
        "other_reviews_count": other_reviews_count,
        "rating_distribution": rating_distribution,
        "positive_reviews_percentage": positive_reviews_percentage,
        "last_rating_update": last_rating_update,
        "qr_page_visits": qr_page_visits,
        "reviews_redirected_google": reviews_redirected_google,
        "reviews_kept_private": reviews_kept_private,
        "conversion_rate": conversion_rate,
        "last_review_update": last_review_update,
        "google_reviews_count": google_reviews_count,
    }

    return starshield_render(
        request,
        "etablissement/overview.html",
        context=context,
        page_name="etablissement",
    )
