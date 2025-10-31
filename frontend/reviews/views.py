import logging

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .forms import FeedbackForm
from auths.models import Etablissement
from .models import Review, ReviewAnalytics
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

    print(rating_array)

    context = {
        "etablissement": etablissement,
        "rating_array": rating_array,
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

    ReviewAnalytics.objects.create(
        etablissement=etablissement,
        type="internal_feedback",
    )
    return render(request, "reviews/feedback_thanks.html")


def feedback_thanks_view(request: HttpRequest, identifier: str) -> HttpResponse:
    etablissement = get_etablissement_by_identifier(identifier)
    if not etablissement:
        return HttpResponseNotFound()

    return render(request, "reviews/feedback_thanks.html")
