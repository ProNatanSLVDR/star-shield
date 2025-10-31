import logging

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .forms import FeedbackForm
from auths.models import Etablissement
from .models import Review

logger = logging.getLogger(__name__)


def feedback_view(request: HttpRequest, identifier: str) -> HttpResponse:
    if not identifier:
        return HttpResponseNotFound()

    try:
        etablissement = Etablissement.objects.get(slug=identifier)
    except Etablissement.DoesNotExist:
        try:
            etablissement = Etablissement.objects.get(uuid=identifier)
        except (Etablissement.DoesNotExist, ValueError):
            return HttpResponseNotFound()

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data["rating"]
            comment = form.cleaned_data.get("comment", "")

            try:
                review = Review.objects.create(
                    etablissement=etablissement,
                    rating=rating,
                    comment=comment,
                    source="internal",
                )

                if rating >= etablissement.review_threshold:
                    if etablissement.new_reviews_uri:
                        return redirect(etablissement.new_reviews_uri)
                    else:
                        logger.warning(
                            f"No Google review URL configured for {etablissement.title}"
                        )

                request.session["feedback_review_id"] = review.id
                return redirect("reviews:feedback_thanks", identifier=identifier)
            except Exception as e:
                logger.error(
                    f"Error creating review for {etablissement.title}: {e}",
                    exc_info=True,
                )
                form.add_error(
                    None,
                    _(
                        "Une erreur s'est produite lors de l'envoi de votre avis. Veuillez réessayer."
                    ),
                )
    else:
        form = FeedbackForm()

    # Get current rating value safely for template
    current_rating = None
    if request.method == "POST":
        current_rating = request.POST.get("rating")
        if current_rating:
            try:
                current_rating = int(current_rating)
            except (ValueError, TypeError):
                current_rating = None

    context = {
        "etablissement": etablissement,
        "form": form,
        "current_rating": current_rating,
    }
    return render(request, "reviews/feedback_form.html", context)


def feedback_thanks_view(request: HttpRequest, identifier: str) -> HttpResponse:
    return render(request, "reviews/feedback_thanks.html")
