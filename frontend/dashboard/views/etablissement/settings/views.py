from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import EtablissementSettingsForm, ToggleFeatureForm


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = EtablissementSettingsForm(request.POST)
        if form.is_valid():
            etablissement.title = form.cleaned_data["title"]
            etablissement.target_rating = form.cleaned_data.get("target_rating")
            etablissement.save()

            messages.success(request, "Paramètres mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:settings")
    else:
        form = EtablissementSettingsForm(
            initial={
                "title": etablissement.title,
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
@require_POST
def toggle_feature_view(request):
    """HTMX endpoint to toggle etablissement features instantly."""
    etablissement = request.etablissement

    # Create form with POST data
    form = ToggleFeatureForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Données invalides.")
        return starshield_render(
            request,
            "etablissement/partials/feature_toggle.html",
            context={"etablissement": etablissement},
        )

    feature = form.cleaned_data["feature"]

    # Get the new state from the form
    # For checkboxes, if checked they send "on", if unchecked they don't send the field
    # So we check if the feature field exists in POST and equals "on"
    if feature == "review_filtering_enabled":
        # Checkbox sends "on" when checked, or nothing when unchecked
        new_state = request.POST.get("review_filtering_enabled") == "on"
    elif feature == "roulette_enabled":
        new_state = request.POST.get("roulette_enabled") == "on"
    else:
        messages.error(request, "Fonctionnalité invalide.")
        return starshield_render(
            request,
            "etablissement/partials/feature_toggle.html",
            context={"etablissement": etablissement},
        )

    # Update the feature
    setattr(etablissement, feature, new_state)
    etablissement.save()

    # Refresh etablissement from DB to ensure we have latest state
    etablissement.refresh_from_db()

    # Return the updated features partial with all features
    return starshield_render(
        request,
        "etablissement/partials/feature_toggle.html",
        context={"etablissement": etablissement},
    )
