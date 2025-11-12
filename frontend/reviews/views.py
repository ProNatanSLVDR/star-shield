import logging
from django.contrib.admin.sites import login_not_required
from django.shortcuts import redirect, render
from django.urls import reverse
from .models import ReviewAnalytics, Review
from .forms import FeedbackForm
from .utils import (
    get_etablissement_by_identifier,
    build_feedback_context,
    get_valid_session_key,
    set_valid_session_key,
)

logger = logging.getLogger(__name__)


@login_not_required
def feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

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
        else:
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
