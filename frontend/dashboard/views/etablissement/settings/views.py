from django.shortcuts import redirect
from django.contrib import messages
from frontend.dashboard.render import starshield_render
from frontend.reviews.utils import build_feedback_context
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from .forms import ReviewSettingsForm


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    context = {
        "etablissement": etablissement,
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
            etablissement.review_show_etablissement_pill = form.cleaned_data[
                "review_show_etablissement_pill"
            ]
            etablissement.review_page_label = form.cleaned_data.get(
                "review_page_label", ""
            )
            etablissement.review_page_text = form.cleaned_data.get(
                "review_page_text", ""
            )
            etablissement.save()

            messages.success(
                request, "Paramètres de la page de feedback mis à jour avec succès."
            )
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
    preview_context = build_feedback_context(request, etablissement, identifier)

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
