from datetime import timedelta

from django.utils import timezone

from apps.private.dashboard.render import starshield_render
from apps.public.reviews.models import Review
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)


@google_gmb_connected_required
@selected_etablissement_required
def historique_view(request):
    return starshield_render(
        request,
        "etablissement/ai_responses/historique.html",
        page_name="ai_responses_historique",
    )


@google_gmb_connected_required
@selected_etablissement_required
def historique_content_partial(request):
    etablissement = request.etablissement
    period = request.GET.get("period", "30")

    # Build date filter
    now = timezone.now()
    date_filter = {}
    if period != "all":
        try:
            days = int(period)
        except ValueError:
            days = 30
        date_filter["reply_date__gte"] = now - timedelta(days=days)

    # Query reviews that have replies
    replied_reviews = Review.objects.filter(
        etablissement=etablissement,
        source="google",
        reply_comment__isnull=False,
        **date_filter,
    ).order_by("-reply_date")

    # Stats
    total_replies = replied_reviews.count()
    ai_replies = replied_reviews.filter(reply_type="ai").count()
    google_replies = replied_reviews.filter(reply_type="google").count()

    stats = [
        {
            "label": "Total réponses",
            "value": total_replies,
            "icon": "fa-solid fa-reply-all",
            "color": "primary",
            "bg": "rgba(13, 110, 253, 0.1)",
        },
        {
            "label": "Réponses IA",
            "value": ai_replies,
            "icon": "fa-solid fa-robot",
            "color": "purple",
            "bg": "rgba(111, 66, 193, 0.1)",
        },
        {
            "label": "Réponses Google",
            "value": google_replies,
            "icon": "fa-brands fa-google",
            "color": "success",
            "bg": "rgba(25, 135, 84, 0.1)",
        },
    ]

    # Build table data
    headers = [
        {
            "label": "Date",
            "key": "date",
            "orderable": True,
            "icon": "fa-solid fa-calendar",
        },
        {
            "label": "Auteur",
            "key": "reviewer",
            "searchable": True,
            "icon": "fa-solid fa-user",
        },
        {
            "label": "Note",
            "key": "rating",
            "centered": True,
            "orderable": True,
            "icon": "fa-solid fa-star",
        },
        {
            "label": "Avis",
            "key": "review_excerpt",
            "searchable": True,
            "icon": "fa-solid fa-comment",
        },
        {
            "label": "Réponse",
            "key": "reply_excerpt",
            "searchable": True,
            "icon": "fa-solid fa-reply",
        },
        {
            "label": "Type",
            "key": "reply_type",
            "centered": True,
            "orderable": True,
            "icon": "fa-solid fa-tag",
        },
    ]

    rows = []
    for review in replied_reviews:
        reviewer_name = "Anonyme"
        if review.google_reviewer_data and review.google_reviewer_data.get("displayName"):
            reviewer_name = review.google_reviewer_data["displayName"]

        # Truncate long texts for display
        review_excerpt = (review.comment or "")[:80]
        if len(review.comment or "") > 80:
            review_excerpt += "..."

        reply_excerpt = (review.reply_comment or "")[:80]
        if len(review.reply_comment or "") > 80:
            reply_excerpt += "..."

        # Stars display
        stars_html = ""
        for i in range(1, 6):
            if i <= review.rating:
                stars_html += '<i class="fa-solid fa-star text-warning"></i>'
            else:
                stars_html += '<i class="fa-regular fa-star text-muted"></i>'

        # Reply type badge
        is_ai = review.reply_type == "ai"
        type_label = "IA" if is_ai else "Google"
        type_variant = "primary" if is_ai else "secondary"

        reply_date = review.reply_date or review.updated_at

        rows.append(
            {
                "date": {
                    "value": reply_date.strftime("%d/%m/%Y %H:%M") if reply_date else "-",
                    "sort_value": reply_date.timestamp() if reply_date else 0,
                },
                "reviewer": reviewer_name,
                "rating": {
                    "type": "html",
                    "value": stars_html,
                    "centered": True,
                    "sort_value": review.rating,
                },
                "review_excerpt": review_excerpt,
                "reply_excerpt": reply_excerpt,
                "reply_type": {
                    "type": "badge",
                    "value": type_label,
                    "variant": type_variant,
                    "sort_value": 1 if is_ai else 0,
                },
            }
        )

    context = {
        "stats": stats,
        "table_data": {
            "headers": headers,
            "rows": rows,
        },
        "current_period": period,
    }

    return starshield_render(
        request,
        "etablissement/ai_responses/historique_content_partial.html",
        context=context,
    )
