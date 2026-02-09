from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from apps.private.dashboard.render import starshield_render
from apps.public.reviews.models import Review
from apps.tasks_api.services.ai_response_service import (
    approve_ai_response,
    regenerate_ai_response,
    reject_ai_response,
)
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)


def _get_next_review(etablissement):
    """Get the next review to process (pending or flagged, most recent first)."""
    return (
        Review.objects.filter(
            etablissement=etablissement,
            source="google",
            ai_response_status__in=["pending", "flagged"],
        )
        .order_by("-writen_at")
        .first()
    )


def _get_remaining_count(etablissement):
    """Count remaining reviews to process."""
    return Review.objects.filter(
        etablissement=etablissement,
        source="google",
        ai_response_status__in=["pending", "flagged"],
    ).count()


def _get_reviewer_name(review):
    if review and review.google_reviewer_data and review.google_reviewer_data.get("displayName"):
        return review.google_reviewer_data["displayName"]
    return "Anonyme"


@google_gmb_connected_required
@selected_etablissement_required
def pending_view(request):
    return starshield_render(
        request,
        "etablissement/ai_responses/pending.html",
        page_name="ai_responses_pending",
    )


@google_gmb_connected_required
@selected_etablissement_required
def pending_content_partial(request):
    etablissement = request.etablissement

    review = _get_next_review(etablissement)
    remaining = _get_remaining_count(etablissement)

    context = {
        "review": review,
        "reviewer_name": _get_reviewer_name(review),
        "remaining_count": remaining,
    }

    return starshield_render(
        request,
        "etablissement/ai_responses/pending_content_partial.html",
        context=context,
    )


@require_POST
@google_gmb_connected_required
@selected_etablissement_required
def approve_review_view(request, review_id):
    review = Review.objects.filter(
        id=review_id,
        etablissement=request.etablissement,
        ai_response_status__in=["pending", "flagged"],
    ).first()

    if not review:
        messages.error(request, "Avis non trouvé.")
        return HttpResponse(status=404)

    edited_comment = request.POST.get("edited_comment", "").strip() or None
    success = approve_ai_response(review.id, edited_comment=edited_comment)

    if success:
        messages.success(request, "Réponse publiée sur Google avec succès.")
    else:
        messages.error(request, "Erreur lors de la publication de la réponse.")

    return starshield_render(request, hx_triggers={"refreshPendingList": True})


@require_POST
@google_gmb_connected_required
@selected_etablissement_required
def reject_review_view(request, review_id):
    review = Review.objects.filter(
        id=review_id,
        etablissement=request.etablissement,
        ai_response_status__in=["pending", "flagged"],
    ).first()

    if not review:
        messages.error(request, "Avis non trouvé.")
        return HttpResponse(status=404)

    success = reject_ai_response(review.id)

    if success:
        messages.success(request, "Réponse rejetée.")
    else:
        messages.error(request, "Erreur lors du rejet de la réponse.")

    return starshield_render(request, hx_triggers={"refreshPendingList": True})


@require_POST
@google_gmb_connected_required
@selected_etablissement_required
def regenerate_review_view(request, review_id):
    review = Review.objects.filter(
        id=review_id,
        etablissement=request.etablissement,
        ai_response_status__in=["pending", "flagged"],
    ).first()

    if not review:
        messages.error(request, "Avis non trouvé.")
        return HttpResponse(status=404)

    new_draft = regenerate_ai_response(review.id)

    if new_draft:
        messages.success(request, "Nouvelle réponse générée.")
    else:
        messages.error(request, "Erreur lors de la régénération.")

    return starshield_render(request, hx_triggers={"refreshPendingList": True})
