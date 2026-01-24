import logging

from django.contrib.admin.sites import login_not_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from starshield.qrcodes import generate_qrcode_png

from .forms import FeedbackForm
from .models import Review, ReviewAnalytics
from .utils import (
    build_feedback_context,
    get_etablissement_by_identifier,
    get_valid_session_key,
    set_valid_session_key,
)

logger = logging.getLogger(__name__)


@login_not_required
def feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    # Show inactive page if establishment is inactive
    if not etablissement.active:
        context = {
            "feedback_context": build_feedback_context(etablissement, identifier, mode="inactive"),
        }
        return render(request, "reviews/feedback_base.html", context)

    analytics_key = f"review_page_consulted_{etablissement.id}"
    if not get_valid_session_key(request, analytics_key):
        ReviewAnalytics.objects.create(
            etablissement=etablissement,
            type="feedback_viewed",
        )
        set_valid_session_key(request, analytics_key, True)

    context = {
        "feedback_context": build_feedback_context(etablissement, identifier, mode="main"),
    }
    return render(request, "reviews/feedback_base.html", context)


@login_not_required
def external_feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    analytics_key = f"feedback_external_{etablissement.id}"
    if not get_valid_session_key(request, analytics_key):
        ReviewAnalytics.objects.create(
            etablissement=etablissement,
            type="feedback_external",
        )
        set_valid_session_key(request, analytics_key, True)

    return redirect(etablissement.new_reviews_uri)


@login_not_required
def internal_feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    prefilled_rating = None

    # si la page de feedback interne n'a pas été consultée depuis plus de 5 minutes, on crée un objet ReviewAnalytics
    analytics_key = f"internal_feedback_consulted_{etablissement.id}"
    if not get_valid_session_key(request, analytics_key):
        ReviewAnalytics.objects.create(
            etablissement=etablissement,
            type="feedback_internal_viewed",
        )
        set_valid_session_key(request, analytics_key, True)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data["rating"]
            comment = form.cleaned_data.get("comment", "")

            # si le feedback interne n'a pas été soumis depuis plus de 5 minutes, on crée un objet Review
            analytics_key = f"internal_feedback_{etablissement.id}"
            valid_session_key = get_valid_session_key(request, analytics_key)
            if not valid_session_key:
                review_object = Review.objects.create(
                    etablissement=etablissement,
                    rating=rating,
                    comment=comment,
                    source="internal",
                )
                ReviewAnalytics.objects.create(
                    etablissement=etablissement,
                    type="feedback_internal_submitted",
                )
                set_valid_session_key(request, analytics_key, review_object.id)

            # si le feedback interne a déjà été soumis depuis plus de 5 minutes, on met à jour l'objet Review
            else:
                review_object = Review.objects.get(id=valid_session_key)
                review_object.rating = rating
                review_object.comment = comment
                review_object.save()

            return redirect(reverse("reviews:feedback_thanks", args=[identifier]))
        prefilled_rating = form.data.get("rating")
        prefilled_rating = int(prefilled_rating) if prefilled_rating else None

    else:
        rating_param = request.GET.get("rating")
        initial_data = {}

        if rating_param:
            try:
                rating = int(rating_param)
                if 1 <= rating <= 5:
                    initial_data["rating"] = rating
                    prefilled_rating = rating
            except (ValueError, TypeError):
                pass

        form = FeedbackForm(initial=initial_data)

    context = {
        "feedback_context": build_feedback_context(
            etablissement,
            identifier,
            mode="internal",
            form=form,
            prefilled_rating=prefilled_rating,
        ),
    }
    return render(request, "reviews/feedback_base.html", context)


@login_not_required
def feedback_thanks_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    context = {
        "feedback_context": build_feedback_context(etablissement, identifier, mode="thanks"),
    }
    return render(
        request,
        "reviews/feedback_base.html",
        context=context,
    )


@login_not_required
def qr_code_image_view(request, identifier=None):
    """Generate and return QR code image as PNG."""
    etablissement = get_etablissement_by_identifier(identifier)

    # Build the feedback URL
    feedback_url = request.build_absolute_uri(reverse("reviews:feedback", args=[identifier]))

    # Get customization parameters from query string (for preview) or database
    fill_color = request.GET.get("fill_color") or etablissement.qr_fill_color or "#000000"
    fill_color_secondary = request.GET.get("fill_color_secondary") or etablissement.qr_fill_color_secondary or "#000000"
    background_color = request.GET.get("background_color") or etablissement.qr_background_color or "#FFFFFF"
    style = request.GET.get("style") or etablissement.qr_style or "square"
    color_mask = request.GET.get("color_mask") or etablissement.qr_color_mask or "solid"

    # Get logo file if exists (using Django's .open() which works for both local and cloud storage)
    logo_file = None
    if etablissement.qr_logo:
        try:
            logo_file = etablissement.qr_logo.open()
        except Exception as e:
            logger.debug(f"Could not open QR logo file for etablissement {etablissement.id}: {e}")
            logo_file = None

    # Generate QR code PNG
    try:
        qr_image_bytes = generate_qrcode_png(
            link=feedback_url,
            fill_color=fill_color,
            fill_color_secondary=fill_color_secondary,
            background_color=background_color,
            style=style,
            color_mask=color_mask,
            logo_file=logo_file,
        )

        response = HttpResponse(qr_image_bytes, content_type="image/png")
        return response
    except Exception as e:
        logger.error(f"Error generating QR code for etablissement {etablissement.id}: {e}", exc_info=True)
        # Return a simple error response or default QR code
        try:
            qr_image_bytes = generate_qrcode_png(
                link=feedback_url,
                fill_color="#000000",
                fill_color_secondary="#000000",
                background_color="#FFFFFF",
                style="square",
                color_mask="solid",
            )
            response = HttpResponse(qr_image_bytes, content_type="image/png")
            return response
        except Exception:
            # If even default fails, return 500
            return HttpResponse("Error generating QR code", status=500)
