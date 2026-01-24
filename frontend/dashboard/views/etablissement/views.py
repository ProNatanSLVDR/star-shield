import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, Count, IntegerField, Q, When
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from frontend.dashboard.render import starshield_render
from frontend.reviews.models import Review, ReviewAnalytics
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from tasks_api.models import TaskExecution
from tasks_api.services.queue_service import enqueue_refresh_task


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
    ordered_reviews = reviews_queryset.order_by("-writen_at", "-created_at")

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
    latest_reviews = ordered_reviews.filter(writen_at__gte=timezone.now() - timedelta(days=15))

    chart_payload = {
        "history": rating_history_points,
        "goal": goal_projection_points,
    }

    stats_items = [
        {
            "label": "Note actuelle",
            "value": current_rating if current_rating else "-",
            "icon": "fa-solid fa-gauge-high",
        },
        {
            "label": "Visites du QR Code",
            "value": qr_page_visits if qr_page_visits else "-",
            "icon": "fa-solid fa-qrcode",
        },
        {
            "label": "Redirections Google",
            "value": reviews_redirected_google if reviews_redirected_google else "-",
            "icon": "fa-solid fa-arrow-up-right-from-square",
        },
        {
            "label": "Redirections Internes",
            "value": reviews_kept_private if reviews_kept_private else "-",
            "icon": "fa-solid fa-lock",
        },
        {
            "label": "Avis Internes",
            "value": internal_reviews_count if internal_reviews_count else "-",
            "icon": "fa-solid fa-inbox",
        },
        {
            "label": "Avis Google",
            "value": google_reviews_count if google_reviews_count else "-",
            "icon": "fa-brands fa-google",
        },
        {
            "label": "Avis Total",
            "value": total_reviews if total_reviews else "-",
            "icon": "fa-solid fa-star",
        },
        {
            "label": "Dernier Avis",
            "value": latest_reviews.first().writen_at if latest_reviews.exists() else "-",
            "icon": "fa-solid fa-clock-rotate-left",
        },
    ]

    context = {
        "etablissement": etablissement,
        "chart_payload_json": json.dumps(chart_payload),
        "stats_items": stats_items,
        "starshield_feedback_url": reverse("reviews:feedback", args=[etablissement.uuid]),
        "range_8": list(range(8)),
        "latest_reviews": list(latest_reviews),
        "total_reviews": total_reviews,
        "rating_distribution": rating_distribution,
    }

    return starshield_render(
        request,
        "etablissement/overview.html",
        context=context,
        page_name="etablissement",
    )


@google_gmb_connected_required
@selected_etablissement_required
def avis_view(request):
    etablissement = request.etablissement

    # Get query parameters
    source_filter = request.GET.get("source", "all")
    rating_filter = request.GET.get("rating", "all")
    date_preset = request.GET.get("date_preset", "30days")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    order_by = request.GET.get("order_by", "date")
    order_dir = request.GET.get("order_dir", "desc")
    page_number = request.GET.get("page", 1)

    # Handle date presets
    # If custom dates are provided, don't use preset
    if date_from or date_to:
        date_preset = ""

    if date_preset:
        today = timezone.now().date()
        if date_preset == "7days":
            date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif date_preset == "30days":
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif date_preset == "this_month":
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif date_preset == "3months":
            date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif date_preset == "all_time":
            all_reviews = Review.objects.filter(etablissement=etablissement)
            oldest_review = (
                all_reviews.extra(select={"review_date": "COALESCE(writen_at, created_at)"})
                .order_by("review_date")
                .first()
            )
            if oldest_review:
                review_date = oldest_review.writen_at or oldest_review.created_at
                if review_date:
                    date_from = review_date.date().strftime("%Y-%m-%d")
            newest_review = (
                all_reviews.extra(select={"review_date": "COALESCE(writen_at, created_at)"})
                .order_by("-review_date")
                .first()
            )
            if newest_review:
                review_date = newest_review.writen_at or newest_review.created_at
                if review_date:
                    date_to = review_date.date().strftime("%Y-%m-%d")

    # Start with base queryset
    reviews_queryset = Review.objects.filter(etablissement=etablissement)

    # Apply source filter
    if source_filter != "all":
        reviews_queryset = reviews_queryset.filter(source=source_filter)

    # Apply rating filter
    if rating_filter != "all":
        try:
            rating_value = int(rating_filter)
            if 1 <= rating_value <= 5:
                reviews_queryset = reviews_queryset.filter(rating=rating_value)
        except ValueError:
            pass

    # Apply date filter
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            date_from_dt = timezone.make_aware(datetime.combine(date_from_obj, datetime.min.time()))
            reviews_queryset = reviews_queryset.filter(
                Q(writen_at__gte=date_from_dt) | (Q(writen_at__isnull=True) & Q(created_at__gte=date_from_dt))
            )
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            date_to_dt = timezone.make_aware(datetime.combine(date_to_obj, datetime.max.time()))
            reviews_queryset = reviews_queryset.filter(
                Q(writen_at__lte=date_to_dt) | (Q(writen_at__isnull=True) & Q(created_at__lte=date_to_dt))
            )
        except ValueError:
            pass

    # Apply sorting
    if order_by == "rating":
        if order_dir == "asc":
            reviews_queryset = reviews_queryset.order_by("rating", "-writen_at", "-created_at")
        else:
            reviews_queryset = reviews_queryset.order_by("-rating", "-writen_at", "-created_at")
    else:  # order_by == "date"
        if order_dir == "asc":
            reviews_queryset = reviews_queryset.extra(select={"sort_date": "COALESCE(writen_at, created_at)"}).order_by(
                "sort_date"
            )
        else:
            reviews_queryset = reviews_queryset.extra(select={"sort_date": "COALESCE(writen_at, created_at)"}).order_by(
                "-sort_date"
            )

    # Pagination
    paginator = Paginator(reviews_queryset, 50)
    try:
        page_number = int(page_number)
        page_obj = paginator.page(page_number)
    except (ValueError, TypeError, PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # Get filter counts for UI - single query using aggregation
    base_queryset = Review.objects.filter(etablissement=etablissement)
    counts = base_queryset.aggregate(
        total_reviews=Count("id"),
        google_reviews_count=Count(Case(When(source="google", then=1), output_field=IntegerField())),
        internal_reviews_count=Count(Case(When(source="internal", then=1), output_field=IntegerField())),
        rating_1_count=Count(Case(When(rating=1, then=1), output_field=IntegerField())),
        rating_2_count=Count(Case(When(rating=2, then=1), output_field=IntegerField())),
        rating_3_count=Count(Case(When(rating=3, then=1), output_field=IntegerField())),
        rating_4_count=Count(Case(When(rating=4, then=1), output_field=IntegerField())),
        rating_5_count=Count(Case(When(rating=5, then=1), output_field=IntegerField())),
    )

    total_reviews = counts["total_reviews"]
    google_reviews_count = counts["google_reviews_count"]
    internal_reviews_count = counts["internal_reviews_count"]
    rating_counts = {
        1: counts["rating_1_count"],
        2: counts["rating_2_count"],
        3: counts["rating_3_count"],
        4: counts["rating_4_count"],
        5: counts["rating_5_count"],
    }

    context = {
        "etablissement": etablissement,
        "reviews": page_obj,
        "total_reviews": total_reviews,
        "google_reviews_count": google_reviews_count,
        "internal_reviews_count": internal_reviews_count,
        "rating_counts": rating_counts,
        "filters": {
            "source": source_filter,
            "rating": rating_filter,
            "date_preset": date_preset,
            "date_from": date_from,
            "date_to": date_to,
            "order_by": order_by,
            "order_dir": order_dir,
        },
    }

    return starshield_render(
        request,
        "etablissement/avis.html",
        context=context,
        page_name="avis",
    )


@google_gmb_connected_required
@selected_etablissement_required
@require_POST
def refresh_reviews_view(request):
    """
    Refresh reviews for the selected etablissement.
    Checks if a refresh was done recently (within 30 minutes) and prevents
    multiple refreshes in a short time period.
    """
    etablissement = request.etablissement

    # Check for latest successful refresh task
    latest_refresh = (
        TaskExecution.objects.filter(
            etablissement=etablissement,
            task_type="fetch_reviews_refresh",
            status="success",
        )
        .order_by("-completed_at")
        .first()
    )

    # Rate limiting: 30 minutes between refreshes
    if latest_refresh and latest_refresh.completed_at:
        time_since_refresh = timezone.now() - latest_refresh.completed_at
        if time_since_refresh < timedelta(minutes=30):
            minutes_remaining = 30 - int(time_since_refresh.total_seconds() / 60)
            messages.warning(
                request,
                f"Un rafraîchissement a déjà été effectué récemment. Veuillez attendre {minutes_remaining} minute(s) avant d'en demander un nouveau.",
            )
            return redirect("dashboard:etablissement:overview")

    # Enqueue refresh task
    try:
        enqueue_refresh_task(etablissement.id)
        messages.success(
            request, "Le rafraîchissement des avis a été demandé avec succès. Les données seront mises à jour sous peu."
        )
    except Exception:
        messages.error(
            request,
            "Une erreur est survenue lors de la demande de rafraîchissement. Veuillez réessayer plus tard.",
        )

    return redirect("dashboard:etablissement:overview")
