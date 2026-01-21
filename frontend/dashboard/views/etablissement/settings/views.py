from django.shortcuts import redirect
from django.contrib import messages
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from .forms import EtablissementSettingsForm


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = EtablissementSettingsForm(request.POST)
        if form.is_valid():
            etablissement.title = form.cleaned_data["title"]
            etablissement.target_rating = form.cleaned_data.get("target_rating")
            etablissement.review_filtering_enabled = form.cleaned_data.get("review_filtering_enabled", False)
            etablissement.roulette_enabled = form.cleaned_data.get("roulette_enabled", False)
            etablissement.save()

            messages.success(request, "Paramètres mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:settings")
    else:
        form = EtablissementSettingsForm(
            initial={
                "title": etablissement.title,
                "target_rating": etablissement.target_rating,
                "review_filtering_enabled": etablissement.review_filtering_enabled,
                "roulette_enabled": etablissement.roulette_enabled,
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
