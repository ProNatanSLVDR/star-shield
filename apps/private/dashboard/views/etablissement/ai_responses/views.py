from django.contrib import messages
from django.shortcuts import redirect

from apps.private.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import AiResponseSettingsForm


@google_gmb_connected_required
@selected_etablissement_required
def ai_responses_settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = AiResponseSettingsForm(request.POST)
        if form.is_valid():
            etablissement.ai_response_tone = form.cleaned_data["ai_response_tone"]
            etablissement.ai_response_length = form.cleaned_data["ai_response_length"]
            etablissement.ai_response_language = form.cleaned_data["ai_response_language"]
            etablissement.ai_response_validation_required = form.cleaned_data["ai_response_validation_required"]
            etablissement.ai_response_malicious_protection = form.cleaned_data["ai_response_malicious_protection"]
            etablissement.save()

            messages.success(request, "Paramètres des réponses IA mis à jour avec succès.")
            return redirect("dashboard:etablissement:ai_responses:settings")
    else:
        form = AiResponseSettingsForm(
            initial={
                "ai_response_tone": etablissement.ai_response_tone,
                "ai_response_length": etablissement.ai_response_length,
                "ai_response_language": etablissement.ai_response_language,
                "ai_response_validation_required": etablissement.ai_response_validation_required,
                "ai_response_malicious_protection": etablissement.ai_response_malicious_protection,
            }
        )

    context = {
        "etablissement": etablissement,
        "form": form,
    }

    return starshield_render(
        request,
        "etablissement/ai_responses/settings.html",
        context=context,
        page_name="ai_responses_settings",
    )
