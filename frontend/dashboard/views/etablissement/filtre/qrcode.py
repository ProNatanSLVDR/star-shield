from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import QRCodeSettingsForm


@login_required
@google_gmb_connected_required
@selected_etablissement_required
def qr_code_settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        # Handle logo deletion
        if request.POST.get("delete_logo"):
            etablissement.qr_logo.delete(save=False)
            etablissement.qr_logo = None
            etablissement.save()
            messages.success(request, "Logo supprimé avec succès.")
            return redirect("dashboard:etablissement:filtre:qrcode")

        form = QRCodeSettingsForm(request.POST, request.FILES)
        if form.is_valid():
            etablissement.qr_fill_color = form.cleaned_data["qr_fill_color"]
            etablissement.qr_fill_color_secondary = form.cleaned_data["qr_fill_color_secondary"]
            etablissement.qr_background_color = form.cleaned_data["qr_background_color"]
            etablissement.qr_style = form.cleaned_data["qr_style"]
            etablissement.qr_color_mask = form.cleaned_data["qr_color_mask"]

            # Handle logo upload
            if "qr_logo" in request.FILES:
                etablissement.qr_logo = request.FILES["qr_logo"]

            etablissement.save()

            messages.success(request, "Paramètres du QR code mis à jour avec succès.")
            return redirect("dashboard:etablissement:filtre:qrcode")
    else:
        form = QRCodeSettingsForm(
            initial={
                "qr_fill_color": etablissement.qr_fill_color or "#000000",
                "qr_fill_color_secondary": etablissement.qr_fill_color_secondary or "#000000",
                "qr_background_color": etablissement.qr_background_color or "#FFFFFF",
                "qr_style": etablissement.qr_style or "square",
                "qr_color_mask": etablissement.qr_color_mask or "solid",
            }
        )

    # Build QR code image URL
    identifier = str(etablissement.uuid)
    qr_code_url = reverse("reviews:qr_code", args=[identifier])

    context = {
        "etablissement": etablissement,
        "form": form,
        "qr_code_url": qr_code_url,
    }

    return starshield_render(
        request,
        "etablissement/filtre/qrcode.html",
        context=context,
        page_name="qr_code",
    )
