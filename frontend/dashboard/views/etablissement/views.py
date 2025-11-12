from django.urls import reverse
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

    current_rating = rating_history_points[-1]["rating"] if rating_history_points else None

    goal_rating = None
    if etablissement.target_rating is not None:
        goal_rating = float(etablissement.target_rating)

    goal_projection_points: list[dict] = []
    if goal_rating is not None:
        origin_date = rating_history_qs.last().created_at if rating_history_points else timezone.now()

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
    ordered_reviews = reviews_queryset.order_by("-created_at")

    total_reviews = reviews_queryset.count()

    google_reviews_count = reviews_queryset.filter(source="google").count()
    internal_reviews_count = reviews_queryset.filter(source="internal").count()

    rating_distribution: list[dict] = []
    for star in range(5, 0, -1):
        rating_distribution.append(
            {
                "rating": str(star),
                "count": reviews_queryset.filter(rating=star).count(),
                "google_count": reviews_queryset.filter(rating=star, source="google").count(),
                "internal_count": reviews_queryset.filter(rating=star, source="internal").count(),
            }
        )

    # Analytics stats from ReviewAnalytics
    analytics_queryset = ReviewAnalytics.objects.filter(etablissement=etablissement)
    qr_page_visits = analytics_queryset.filter(type="feedback_viewed").count()
    reviews_redirected_google = analytics_queryset.filter(type="feedback_external").count()
    reviews_kept_private = analytics_queryset.filter(type="feedback_internal_viewed").count()

    # Last review update time
    latest_reviews: list[Review] = list[Review](ordered_reviews[:5])

    last_review_update = None
    if latest_reviews:
        last_review_update = latest_reviews[0].created_at

    chart_payload = {
        "history": rating_history_points,
        "goal": goal_projection_points,
    }

    context = {
        "etablissement": etablissement,
        "chart_payload_json": json.dumps(chart_payload),
        "current_rating": current_rating,
        "total_reviews": total_reviews,
        "google_reviews_count": google_reviews_count,
        "internal_reviews_count": internal_reviews_count,
        "rating_distribution": rating_distribution,
        "qr_page_visits": qr_page_visits,
        "reviews_redirected_google": reviews_redirected_google,
        "reviews_kept_private": reviews_kept_private,
        "last_review_update": last_review_update,
        "latest_reviews": latest_reviews,
        "starshield_feedback_url": reverse("reviews:feedback", args=[etablissement.uuid]),
    }

    return starshield_render(
        request,
        "etablissement/overview.html",
        context=context,
        page_name="etablissement",
    )
