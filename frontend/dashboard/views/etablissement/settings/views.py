from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from auths.models import Etablissement
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from utils.qrcodes import generate_qrcode
from .forms import EtablissementSettingsForm


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    # Generate QR code for feedback URL
    identifier = etablissement.slug or str(etablissement.uuid)
    feedback_url = request.build_absolute_uri(
        reverse("reviews:feedback", args=[identifier])
    )
    qr_code_svg = generate_qrcode(feedback_url, size=20)

    if request.method == "POST":
        form = EtablissementSettingsForm(request.POST)
        if form.is_valid():
            # Update etablissement settings
            etablissement.review_threshold = int(form.cleaned_data["review_threshold"])

            # Handle target_rating - empty string becomes None
            target_rating = form.cleaned_data.get("target_rating")
            etablissement.target_rating = (
                target_rating if target_rating is not None else None
            )

            # Handle review_page_label - empty string becomes None
            review_page_label = form.cleaned_data.get("review_page_label", "").strip()
            etablissement.review_page_label = (
                review_page_label if review_page_label else None
            )

            # Handle review_page_text - empty string uses default
            review_page_text = form.cleaned_data.get("review_page_text", "").strip()
            etablissement.review_page_text = (
                review_page_text
                if review_page_text
                else "Votre avis nous aide à offrir un meilleur service !"
            )

            etablissement.save()

            messages.success(request, "Paramètres mis à jour avec succès!")
            return redirect("dashboard:etablissement:overview")
    else:
        # Initialize form with current values
        form = EtablissementSettingsForm(
            initial={
                "review_threshold": str(etablissement.review_threshold),
                "target_rating": str(etablissement.target_rating)
                if etablissement.target_rating
                else "",
                "review_page_label": etablissement.review_page_label or "",
                "review_page_text": etablissement.review_page_text or "",
            }
        )

    context = {
        "form": form,
        "etablissement": etablissement,
        "qr_code_svg": qr_code_svg,
        "feedback_url": feedback_url,
    }

    return starshield_render(
        request,
        "etablissement/settings/settings.html",
        context=context,
        page_name="etablissement_settings",
    )
