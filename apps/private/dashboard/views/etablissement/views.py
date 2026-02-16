import calendar
import json
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, Count, IntegerField, Q, When
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST


from apps.private.auths.models import WeeklyPerformanceSummary
from apps.private.dashboard.render import starshield_render
from apps.public.reviews.models import Review, ReviewAnalytics
from apps.public.roulette.models import RouletteAnalytics, RouletteSpin
from apps.tasks_api.services.queue_service import enqueue_refresh_task
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)


@google_gmb_connected_required
@selected_etablissement_required
def overview_view(request):
    """New overview page with features, general stats, and useful links."""
    etablissement = request.etablissement

    # Get basic stats for the general stats section
    reviews_queryset = Review.objects.filter(etablissement=etablissement)
    total_reviews = reviews_queryset.count()

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

    analytics_queryset = ReviewAnalytics.objects.filter(etablissement=etablissement)
    qr_page_visits = analytics_queryset.filter(type="feedback_viewed").count()

    # General stats for hover section (key metrics only)
    general_stats = [
        {
            "label": "Note actuelle",
            "value": f"{current_rating:.1f}" if current_rating else "-",
            "icon": "fa-solid fa-gauge-high",
        },
        {
            "label": "Avis Total",
            "value": total_reviews if total_reviews else "-",
            "icon": "fa-solid fa-star",
        },
        {
            "label": "Visites QR Code",
            "value": qr_page_visits if qr_page_visits else "-",
            "icon": "fa-solid fa-qrcode",
        },
    ]

    # Recent reviews (last 15 days)
    ordered_reviews = reviews_queryset.order_by("-writen_at", "-created_at")
    latest_reviews = ordered_reviews.filter(writen_at__gte=timezone.now() - timedelta(days=15))

    # Latest weekly summary
    weekly_summary = WeeklyPerformanceSummary.objects.filter(
        etablissement=etablissement,
    ).first()

    details_url = reverse("dashboard:etablissements:details_partial", args=[etablissement.id])

    context = {
        "etablissement": etablissement,
        "starshield_feedback_url": reverse("dashboard:etablissement:qrcodes"),
        "general_stats": general_stats,
        "latest_reviews": list(latest_reviews),
        "weekly_summary": weekly_summary,
        "details_url": details_url,
    }

    return starshield_render(
        request,
        "etablissement/overview.html",
        context=context,
        page_name="etablissement",
    )


@google_gmb_connected_required
@selected_etablissement_required
def stats_view(request):
    """Stats page with detailed overview (chart, stats, rating distribution, recent reviews)."""
    etablissement = request.etablissement

    # Build chart data from actual review publish dates
    reviews_with_dates = (
        Review.objects.filter(etablissement=etablissement, writen_at__isnull=False)
        .order_by("writen_at")
        .values_list("writen_at", "rating")
    )

    # Generate 24 checkpoints: mid-month (15th) + end-of-month for the last 12 months
    today = timezone.now().date()
    checkpoints: list[date] = []
    for months_ago in range(12, 0, -1):
        # Calculate the target month
        month = today.month - months_ago
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        last_day = calendar.monthrange(year, month)[1]
        checkpoints.append(date(year, month, 15))
        checkpoints.append(date(year, month, last_day))

    # Compute running average at each checkpoint
    rating_history_points: list[dict] = []
    running_sum = 0.0
    running_count = 0
    review_iter = iter(reviews_with_dates)
    current_review = next(review_iter, None)

    for checkpoint in checkpoints:
        # Consume all reviews up to and including this checkpoint
        while current_review is not None and current_review[0].date() <= checkpoint:
            running_sum += current_review[1]
            running_count += 1
            current_review = next(review_iter, None)

        if running_count > 0:
            rating_history_points.append(
                {
                    "date": checkpoint.strftime("%Y-%m-%d"),
                    "label": checkpoint.strftime("%d %b %Y"),
                    "rating": round(running_sum / running_count, 2),
                    "total_reviews": running_count,
                }
            )

    current_rating = rating_history_points[-1]["rating"] if rating_history_points else None

    goal_rating = None
    if etablissement.target_rating is not None:
        goal_rating = float(etablissement.target_rating)

    # goal_rating is passed directly to the chart as a horizontal line value

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

    # QR Code statistics
    qr_codes = etablissement.qr_codes.all()
    qr_codes_stats = []
    for qr_code in qr_codes:
        qr_codes_stats.append(
            {
                "name": qr_code.name,
                "routing": qr_code.routing,
                "routing_display": qr_code.get_routing_display(),
                "total_scans": qr_code.scan_count(),
                "scans_today": qr_code.scans_today(),
                "scans_this_week": qr_code.scans_this_week(),
                "scans_this_month": qr_code.scans_this_month(),
                "created_at": qr_code.created_at,
            }
        )

    chart_payload = {
        "history": rating_history_points,
        "goal": goal_rating,
    }

    stats_items = [
        {
            "label": "Note actuelle",
            "value": current_rating if current_rating else "-",
            "icon": "fa-solid fa-gauge-high",
            "description": "Note moyenne calculée à partir de tous les avis reçus",
        },
        {
            "label": "Visites du QR Code",
            "value": qr_page_visits if qr_page_visits else "-",
            "icon": "fa-solid fa-qrcode",
            "description": "Nombre de fois que la page d'avis a été ouverte via un QR code",
        },
        {
            "label": "Redirections Google",
            "value": reviews_redirected_google if reviews_redirected_google else "-",
            "icon": "fa-solid fa-arrow-up-right-from-square",
            "description": "Nombre de clients redirigés vers Google pour laisser un avis",
        },
        {
            "label": "Redirections Internes",
            "value": reviews_kept_private if reviews_kept_private else "-",
            "icon": "fa-solid fa-lock",
            "description": "Nombre de clients ayant donné un avis en interne",
        },
        {
            "label": "Avis Internes",
            "value": internal_reviews_count if internal_reviews_count else "-",
            "icon": "fa-solid fa-inbox",
            "description": "Nombre total d'avis reçus en interne via Starshield",
        },
        {
            "label": "Avis Google",
            "value": google_reviews_count if google_reviews_count else "-",
            "icon": "fa-brands fa-google",
            "description": "Nombre total d'avis publiés sur Google",
        },
        {
            "label": "Avis Total",
            "value": total_reviews if total_reviews else "-",
            "icon": "fa-solid fa-star",
            "description": "Nombre total d'avis toutes sources confondues",
        },
        {
            "label": "Dernier Avis",
            "value": latest_reviews.first().writen_at if latest_reviews.exists() else "-",
            "icon": "fa-solid fa-clock-rotate-left",
            "description": "Date et heure du dernier avis reçu",
        },
    ]

    # Roulette stats
    roulette_spins_played = RouletteAnalytics.objects.filter(etablissement=etablissement, type="roulette_spun").count()
    roulette_prizes_given = RouletteSpin.objects.filter(etablissement=etablissement).count()
    roulette_prizes_redeemed = RouletteSpin.objects.filter(etablissement=etablissement, is_used=True).count()
    roulette_redemption_rate = (
        round((roulette_prizes_redeemed / roulette_prizes_given) * 100, 1) if roulette_prizes_given > 0 else 0
    )

    roulette_stats = [
        {
            "label": "Tours joués",
            "value": roulette_spins_played,
            "icon": "fa-solid fa-rotate",
            "color": "purple",
            "bg": "rgba(111, 66, 193, 0.1)",
        },
        {
            "label": "Prix distribués",
            "value": roulette_prizes_given,
            "icon": "fa-solid fa-gift",
            "color": "primary",
            "bg": "rgba(13, 110, 253, 0.1)",
        },
        {
            "label": "Prix réclamés",
            "value": roulette_prizes_redeemed,
            "icon": "fa-solid fa-check",
            "color": "success",
            "bg": "rgba(25, 135, 84, 0.1)",
        },
        {
            "label": "Taux de réclamation",
            "value": f"{roulette_redemption_rate}%",
            "icon": "fa-solid fa-percent",
            "color": "warning",
            "bg": "rgba(255, 193, 7, 0.1)",
        },
    ]

    context = {
        "etablissement": etablissement,
        "chart_payload_json": json.dumps(chart_payload),
        "stats_items": stats_items,
        "range_8": list(range(8)),
        "latest_reviews": list(latest_reviews),
        "total_reviews": total_reviews,
        "rating_distribution": rating_distribution,
        "qr_codes_stats": qr_codes_stats,
        "roulette_stats": roulette_stats,
    }

    return starshield_render(
        request,
        "etablissement/stats.html",
        context=context,
        page_name="etablissement_stats",
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
            all_reviews = Review.objects.filter(etablissement=etablissement).annotate(
                review_date=Coalesce("writen_at", "created_at")
            )
            oldest_review = all_reviews.order_by("review_date").first()
            if oldest_review:
                review_date = oldest_review.writen_at or oldest_review.created_at
                if review_date:
                    date_from = review_date.date().strftime("%Y-%m-%d")
            newest_review = all_reviews.order_by("-review_date").first()
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
        reviews_queryset = reviews_queryset.annotate(sort_date=Coalesce("writen_at", "created_at"))
        if order_dir == "asc":
            reviews_queryset = reviews_queryset.order_by("sort_date")
        else:
            reviews_queryset = reviews_queryset.order_by("-sort_date")

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

    # Rate limiting: 30 minutes between refreshes
    if etablissement.last_reviews_update:
        time_since_refresh = timezone.now() - etablissement.last_reviews_update
        if time_since_refresh < timedelta(minutes=30):
            minutes_remaining = 30 - int(time_since_refresh.total_seconds() / 60)
            messages.warning(
                request,
                f"Un rafraîchissement a déjà été effectué récemment. Veuillez attendre {minutes_remaining} minute(s) avant d'en demander un nouveau.",
            )
            return redirect("dashboard:etablissement:overview")

    # Mark refresh time immediately to prevent duplicate requests
    etablissement.last_reviews_update = timezone.now()
    etablissement.save(update_fields=["last_reviews_update"])

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
