import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from auths.models import QRCode
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import QRCodeCreateForm, QRCodeSettingsForm


@login_required
@google_gmb_connected_required
@selected_etablissement_required
def qr_code_management_view(request):
    etablissement = request.etablissement

    # Get all QR codes for this establishment
    qr_codes = etablissement.qr_codes.all()

    # Get selected QR code ID from query parameter
    selected_qr_code_id = request.GET.get("qr_code_id")
    selected_qr_code = None

    if selected_qr_code_id:
        try:
            selected_qr_code = get_object_or_404(QRCode, id=selected_qr_code_id, etablissement=etablissement)
        except Exception:
            selected_qr_code = None

    # If no QR code selected, use first one
    if not selected_qr_code:
        selected_qr_code = qr_codes.first()

    if request.method == "POST":
        # Handle update
        if selected_qr_code:
            form = QRCodeSettingsForm(request.POST, request.FILES)
            if form.is_valid():
                # Handle logo deletion
                if request.POST.get("delete_logo"):
                    selected_qr_code.qr_logo.delete(save=False)
                    selected_qr_code.qr_logo = None
                    selected_qr_code.save()
                    messages.success(request, "Logo supprimé avec succès.")
                    return redirect(f"{reverse('dashboard:etablissement:qrcode')}?qr_code_id={selected_qr_code.id}")

                selected_qr_code.name = form.cleaned_data["name"]
                selected_qr_code.routing = form.cleaned_data["routing"]
                selected_qr_code.qr_fill_color = form.cleaned_data["qr_fill_color"]
                selected_qr_code.qr_fill_color_secondary = form.cleaned_data["qr_fill_color_secondary"]
                selected_qr_code.qr_background_color = form.cleaned_data["qr_background_color"]
                selected_qr_code.qr_style = form.cleaned_data["qr_style"]
                selected_qr_code.qr_color_mask = form.cleaned_data["qr_color_mask"]

                if "qr_logo" in request.FILES:
                    selected_qr_code.qr_logo = request.FILES["qr_logo"]

                selected_qr_code.save()
                messages.success(request, "Paramètres du QR code mis à jour avec succès.")
                return redirect(f"{reverse('dashboard:etablissement:qrcodes')}?qr_code_id={selected_qr_code.id}")
        else:
            form = QRCodeSettingsForm(request.POST, request.FILES)
    else:
        # GET request - initialize form
        if selected_qr_code:
            form = QRCodeSettingsForm(
                initial={
                    "name": selected_qr_code.name,
                    "routing": selected_qr_code.routing,
                    "qr_fill_color": selected_qr_code.qr_fill_color,
                    "qr_fill_color_secondary": selected_qr_code.qr_fill_color_secondary,
                    "qr_background_color": selected_qr_code.qr_background_color,
                    "qr_style": selected_qr_code.qr_style,
                    "qr_color_mask": selected_qr_code.qr_color_mask,
                }
            )
        else:
            form = QRCodeSettingsForm()

    # Build QR code image URL
    identifier = str(etablissement.uuid)
    qr_code_url = None
    if selected_qr_code and selected_qr_code.short_code:
        qr_code_url = reverse("reviews:qr_code", args=[identifier]) + f"?short_code={selected_qr_code.short_code}"
    else:
        qr_code_url = reverse("reviews:qr_code", args=[identifier])

    full_qr_code_url = request.build_absolute_uri(qr_code_url)

    qr_code_count = qr_codes.count()
    max_qr_codes = 8
    empty_slots_count = max(0, max_qr_codes - qr_code_count)

    # Create a list of slots: actual QR codes + empty slots
    qr_codes_list = list(qr_codes)
    empty_slots_list = [None] * empty_slots_count
    all_slots = qr_codes_list + empty_slots_list

    context = {
        "etablissement": etablissement,
        "qr_codes": qr_codes,
        "selected_qr_code": selected_qr_code,
        "form": form,
        "qr_code_url": qr_code_url,
        "full_qr_code_url": full_qr_code_url,
        "qr_code_count": qr_code_count,
        "max_qr_codes": max_qr_codes,
        "empty_slots_count": empty_slots_count,
        "limit_reached": qr_code_count >= max_qr_codes,
        "all_slots": all_slots,
    }

    return starshield_render(
        request,
        "etablissement/qrcodes/qrcodes.html",
        context=context,
        page_name="qrcodes",
    )


@login_required
@google_gmb_connected_required
@selected_etablissement_required
def qr_code_create_view(request):
    """View for creating a new QR code (HTMX modal)."""
    etablissement = request.etablissement

    # Check if limit of 8 QR codes has been reached
    qr_code_count = etablissement.qr_codes.count()
    limit_reached = qr_code_count >= 8

    if request.method == "POST":
        if limit_reached:
            form = QRCodeCreateForm(request.POST)
            form.add_error(
                None,
                "Vous avez atteint la limite de 8 QR codes. Supprimez un QR code existant pour en créer un nouveau.",
            )
        else:
            form = QRCodeCreateForm(request.POST)
            if form.is_valid():
                new_qr_code = QRCode.objects.create(
                    etablissement=etablissement, name=form.cleaned_data["name"], routing=form.cleaned_data["routing"]
                )
                messages.success(request, "QR code créé avec succès.")
                # Return empty response to close modal and redirect
                response = HttpResponse()
                response["HX-Trigger"] = json.dumps({"close-modal": True})
                response["HX-Redirect"] = f"{reverse('dashboard:etablissement:qrcodes')}?qr_code_id={new_qr_code.id}"
                return response
    else:
        form = QRCodeCreateForm()

    context = {
        "etablissement": etablissement,
        "form": form,
        "limit_reached": limit_reached,
        "qr_code_count": qr_code_count,
    }

    return starshield_render(
        request,
        "etablissement/qrcodes/create_partial.html",
        context=context,
    )


@login_required
@google_gmb_connected_required
@selected_etablissement_required
@require_http_methods(["GET", "POST"])
def qr_code_delete_partial(request, qr_code_id):
    """
    Partial view for deleting a QR code.
    """
    etablissement = request.etablissement

    qr_code = get_object_or_404(QRCode, id=qr_code_id, etablissement=etablissement)
    qr_code_name = qr_code.name

    if request.method == "POST":
        qr_code.delete()
        messages.success(request, f"Le QR code {qr_code_name} a été supprimé avec succès.")
        return redirect("dashboard:etablissement:qrcodes")

    # GET request - show the form
    context = {
        "qr_code_name": qr_code_name,
        "delete_url": reverse("dashboard:etablissement:qrcode_delete_partial", args=[qr_code.id]),
    }

    return starshield_render(
        request,
        "etablissement/qrcodes/delete_partial.html",
        context=context,
    )
