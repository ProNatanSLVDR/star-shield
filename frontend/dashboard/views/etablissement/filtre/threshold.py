from django.shortcuts import redirect
from django.contrib import messages
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from .forms import ThresholdObjectiveForm


@google_gmb_connected_required
@selected_etablissement_required
def threshold_settings_view(request):
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
            return redirect("dashboard:etablissement:filtre:threshold")
    else:
        form = ThresholdObjectiveForm(
            initial={
                "review_threshold": etablissement.review_threshold,
                "target_rating": etablissement.target_rating,
            }
        )

    context = {
        "etablissement": etablissement,
        "form": form,
        "current_rating": current_rating,
        "total_reviews": total_reviews,
    }

    return starshield_render(
        request,
        "etablissement/filtre/threshold.html",
        context=context,
        page_name="seuil_et_objectif",
    )
