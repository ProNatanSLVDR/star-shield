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

            review = Review.objects.create(
                etablissement=etablissement,
                rating=rating,
                comment=comment,
            )

            if rating >= etablissement.review_threshold:
                return redirect(etablissement.get_google_review_url())

            request.session["feedback_review_id"] = review.id
            return redirect("reviews:feedback_thanks", identifier=identifier)
    else:
        form = FeedbackForm()

    context = {
        "etablissement": etablissement,
        "form": form,
    }
    return render(request, "reviews/feedback_form.html", context)


def feedback_thanks_view(request: HttpRequest) -> HttpResponse:
    return render(request, "reviews/feedback_thanks.html")