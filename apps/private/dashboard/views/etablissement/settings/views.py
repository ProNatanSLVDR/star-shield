from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST

from apps.private.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import ToggleFeatureForm


@google_gmb_connected_required
@selected_etablissement_required
@require_POST
def toggle_feature_view(request):
    """HTMX endpoint to toggle etablissement features instantly."""
    etablissement = request.etablissement

    # Create form with POST data
    form = ToggleFeatureForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Erreur lors de la modification des fonctionnalités.")
        return starshield_render(
            request,
            "etablissement/settings/feature_toggles.html",
            context={"etablissement": etablissement},
        )

    # List of known feature fields
    feature_fields = ["review_filtering_enabled", "roulette_enabled", "ai_responses_enabled"]

    # Process all features: enable if present in POST and equals "on", otherwise disable
    for feature_field in feature_fields:
        new_state = form.cleaned_data.get(feature_field, False)
        setattr(etablissement, feature_field, new_state)

    # Save all changes at once
    etablissement.save()

    # Refresh etablissement from DB to ensure we have latest state
    etablissement.refresh_from_db()

    # Return the updated features partial with all features
    return starshield_render(
        request,
        "etablissement/settings/feature_toggles.html",
        context={"etablissement": etablissement},
    )


ALLOWED_FEATURE_FIELDS = {"roulette_enabled", "ai_responses_enabled", "review_filtering_enabled"}

FEATURE_DISPLAY = {
    "roulette_enabled": ("Roulette", "fa-solid fa-record-vinyl"),
    "ai_responses_enabled": ("Réponses IA", "fa-solid fa-robot"),
    "review_filtering_enabled": ("Filtrage", "fa-solid fa-filter"),
}


@selected_etablissement_required
@require_POST
def toggle_single_feature_view(request):
    """HTMX endpoint to toggle a single feature on/off."""
    etablissement = request.etablissement
    feature = request.POST.get("feature")

    if feature not in ALLOWED_FEATURE_FIELDS:
        return HttpResponseBadRequest("Invalid feature field.")

    current_value = getattr(etablissement, feature)
    setattr(etablissement, feature, not current_value)
    etablissement.save(update_fields=[feature])
    etablissement.refresh_from_db()

    feature_name, icon = FEATURE_DISPLAY[feature]

    return starshield_render(
        request,
        "etablissement/settings/feature_header_toggle_partial.html",
        context={
            "etablissement": etablissement,
            "feature_field": feature,
            "feature_enabled": getattr(etablissement, feature),
            "feature_name": feature_name,
            "icon": icon,
        },
    )
