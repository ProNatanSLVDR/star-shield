import logging
from datetime import timedelta
from django.utils import timezone
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from .models import ReviewAnalytics, Review
from .forms import FeedbackForm
from .utils import get_etablissement_by_identifier, build_feedback_context
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


def feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    # create analytics if not already saved
    # if its set and is older than 1 hour, create a new one
    save_time_str = request.session.get("analytics_review_page_consulted_save_time")
    save_time = parse_datetime(save_time_str) if save_time_str else None

    if not save_time or save_time < timezone.now() - timedelta(minutes=5):
        ReviewAnalytics.objects.create(
            etablissement=etablissement,
            type="review_page_consulted",
        )
        request.session["analytics_review_page_consulted_save_time"] = str(
            timezone.now()
        )
        request.session.modified = True

    context = {
        "feedback_context": build_feedback_context(
            etablissement, identifier, mode="main"
        ),
    }
    return render(request, "reviews/feedback_base.html", context)


def external_feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    ReviewAnalytics.objects.create(
        etablissement=etablissement,
        type="external_feedback",
    )
    return redirect(etablissement.new_reviews_uri)


def internal_feedback_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    prefilled_rating = None

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data["rating"]
            comment = form.cleaned_data.get("comment", "")

            Review.objects.create(
                etablissement=etablissement,
                rating=rating,
                comment=comment,
                source="internal",
            )

            ReviewAnalytics.objects.update_or_create(
                etablissement=etablissement,
                type="internal_feedback",
                id=request.session["review_analytics_id"],
            )

            return redirect(reverse("reviews:feedback_thanks", args=[identifier]))
        else:
            prefilled_rating = form.data.get("rating")
            try:
                prefilled_rating = int(prefilled_rating) if prefilled_rating else None
            except (ValueError, TypeError):
                prefilled_rating = None
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


def feedback_thanks_view(request, identifier=None):
    etablissement = get_etablissement_by_identifier(identifier)

    context = {
        "feedback_context": build_feedback_context(
            etablissement, identifier, mode="thanks"
        ),
    }
    return render(
        request,
        "reviews/feedback_base.html",
        context=context,
    )
