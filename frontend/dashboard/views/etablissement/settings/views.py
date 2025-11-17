from django.shortcuts import redirect
from django.contrib import messages
from frontend.dashboard.render import starshield_render
from frontend.reviews.utils import build_feedback_context
from frontend.reviews.models import Review
from auths.models import RatingHistory
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from .forms import ReviewSettingsForm, EtablissementSettingsForm, ThresholdObjectiveForm


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = EtablissementSettingsForm(request.POST)
        if form.is_valid():
            etablissement.title = form.cleaned_data["title"]
            etablissement.review_threshold = int(form.cleaned_data["review_threshold"])
            etablissement.target_rating = form.cleaned_data.get("target_rating")
            etablissement.save()

            messages.success(request, "Paramètres mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:settings")
    else:
        form = EtablissementSettingsForm(
            initial={
                "title": etablissement.title,
                "review_threshold": etablissement.review_threshold,
                "target_rating": etablissement.target_rating,
            }
        )

    context = {
        "etablissement": etablissement,
        "form": form,
    }

    return starshield_render(
        request,
        "etablissement/settings/index.html",
        context=context,
        page_name="etablissement_settings",
    )


@google_gmb_connected_required
@selected_etablissement_required
def reviews_settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = ReviewSettingsForm(request.POST)
        if form.is_valid():
            etablissement.review_accent_color = form.cleaned_data["review_accent_color"]
            etablissement.review_show_etablissement_pill = form.cleaned_data["review_show_etablissement_pill"]
            etablissement.review_page_label = form.cleaned_data.get("review_page_label", "")
            etablissement.review_page_text = form.cleaned_data.get("review_page_text", "")
            etablissement.save()

            messages.success(request, "Paramètres de la page de feedback mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:reviews")
    else:
        form = ReviewSettingsForm(
            initial={
                "review_accent_color": etablissement.review_accent_color,
                "review_show_etablissement_pill": etablissement.review_show_etablissement_pill,
                "review_page_label": etablissement.review_page_label,
                "review_page_text": etablissement.review_page_text,
            }
        )

    # Build preview context for feedback template
    identifier = str(etablissement.uuid)
    preview_context = build_feedback_context(etablissement, identifier, mode="main")

    context = {
        "etablissement": etablissement,
        "form": form,
        "preview_context": preview_context,
    }

    return starshield_render(
        request,
        "etablissement/settings/reviews.html",
        context=context,
        page_name="etablissement_settings_reviews",
    )


@google_gmb_connected_required
@selected_etablissement_required
def threshold_objective_calculator_view(request):
    etablissement = request.etablissement

    # Get current rating from RatingHistory (latest entry) or calculate from Review
    current_rating = None
    total_reviews = 0

    rating_history = etablissement.rating_history.order_by("-created_at").first()
    if rating_history:
        current_rating = float(rating_history.rating)
        total_reviews = rating_history.total_reviews

    if request.method == "POST":
        form = ThresholdObjectiveForm(request.POST)
        if form.is_valid():
            etablissement.review_threshold = int(form.cleaned_data["review_threshold"])
            etablissement.target_rating = form.cleaned_data.get("target_rating")
            etablissement.save()

            messages.success(request, "Seuil et objectif mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:calculator")
    else:
        form = ThresholdObjectiveForm(
            initial={
                "review_threshold": etablissement.review_threshold,
                "target_rating": etablissement.target_rating,
            }
        )

    card_height = round((etablissement.review_threshold / 5) * 100)
    card_height_reverse = 100 - card_height

    context = {
        "etablissement": etablissement,
        "form": form,
        "current_rating": current_rating,
        "total_reviews": total_reviews,
        "card_height": card_height,
        "card_height_reverse": card_height_reverse,
    }

    return starshield_render(
        request,
        "etablissement/settings/calculator.html",
        context=context,
        page_name="etablissement_settings_calculator",
    )
