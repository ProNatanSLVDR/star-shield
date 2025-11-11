import logging

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse
from .models import ReviewAnalytics, Review
from .forms import FeedbackForm
from .utils import get_etablissement_by_identifier


logger = logging.getLogger(__name__)


def feedback_view(request: HttpRequest, identifier: str) -> HttpResponse:
    if not identifier:
        return HttpResponseNotFound()

    etablissement = get_etablissement_by_identifier(identifier)
    if not etablissement:
        return HttpResponseNotFound()

    ReviewAnalytics.objects.create(
        etablissement=etablissement,
        type="review_page_consulted",
    )

    # pour chaque étoile, on ajoute True si l'étoile est >= au seuil de redirection, False sinon
    # permet de savoir si on redirige vers la page de feedback ou vers la page de redirection Google
    rating_array = []
    for i in range(1, 6):
        if i >= etablissement.review_threshold:
            rating_array.append(True)
        else:
            rating_array.append(False)

    context = {
        "etablissement": etablissement,
        "rating_array": rating_array,
        "internal_feedback_url": request.build_absolute_uri(
            reverse("reviews:internal_feedback", args=[identifier])
        ),
        "external_feedback_url": request.build_absolute_uri(
            reverse("reviews:external_feedback", args=[identifier])
        ),
    }
    return render(request, "reviews/feedback_main.html", context)


def external_feedback_view(request: HttpRequest, identifier: str) -> HttpResponse:
    etablissement = get_etablissement_by_identifier(identifier)
    if not etablissement:
        return HttpResponseNotFound()

    ReviewAnalytics.objects.create(
        etablissement=etablissement,
        type="external_feedback",
    )
    return redirect(etablissement.new_reviews_uri)


def internal_feedback_view(request: HttpRequest, identifier: str) -> HttpResponse:
    etablissement = get_etablissement_by_identifier(identifier)
    if not etablissement:
        return HttpResponseNotFound()

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

            ReviewAnalytics.objects.create(
                etablissement=etablissement,
                type="internal_feedback",
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
        "etablissement": etablissement,
        "form": form,
        "prefilled_rating": prefilled_rating,
        "identifier": identifier,
    }
    return render(request, "reviews/feedback_internal.html", context)


def feedback_thanks_view(request: HttpRequest, identifier: str) -> HttpResponse:
    etablissement = get_etablissement_by_identifier(identifier)
    if not etablissement:
        return HttpResponseNotFound()

    return render(
        request,
        "reviews/feedback_thanks.html",
        context={"etablissement": etablissement},
    )
