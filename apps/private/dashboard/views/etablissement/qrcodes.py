import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.private.auths.models import QRCode
from apps.private.dashboard.render import starshield_render
from apps.public.reviews.utils import get_etablissement_by_identifier
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from starshield.logger import logger
from starshield.qrcodes import generate_qrcode_png

from .forms import QRCodeCreateForm, QRCodeSettingsForm


@login_required
@google_gmb_connected_required
@selected_etablissement_required
def qr_code_management_view(request, short_code=None):
    etablissement = request.etablissement

    # Get all QR codes for this establishment
    qr_codes = etablissement.qr_codes.all()

    # Get selected QR code from short_code path parameter
    selected_qr_code = None

    if short_code:
        selected_qr_code = QRCode.objects.filter(short_code=short_code, etablissement=etablissement).first()

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
                    if selected_qr_code.short_code:
                        return redirect(reverse("dashboard:etablissement:qrcodes", args=[selected_qr_code.short_code]))
                    return redirect("dashboard:etablissement:qrcodes")

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
                if selected_qr_code.short_code:
                    return redirect(reverse("dashboard:etablissement:qrcodes", args=[selected_qr_code.short_code]))
                return redirect("dashboard:etablissement:qrcodes")
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
        qr_code_url = reverse("dashboard:etablissement:qr_code", args=[identifier, selected_qr_code.short_code])
    elif qr_codes.exists():
        # Fallback: if no QR code selected or no short_code, use first QR code's short_code
        first_qr = qr_codes.first()
        if first_qr and first_qr.short_code:
            qr_code_url = reverse("dashboard:etablissement:qr_code", args=[identifier, first_qr.short_code])

    full_qr_code_url = None
    if selected_qr_code and selected_qr_code.short_code:
        full_qr_code_url = request.build_absolute_uri(
            reverse("routing:qr_code_redirect", args=[identifier, selected_qr_code.short_code])
        )

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
                if new_qr_code.short_code:
                    response["HX-Redirect"] = reverse("dashboard:etablissement:qrcodes", args=[new_qr_code.short_code])
                else:
                    response["HX-Redirect"] = reverse("dashboard:etablissement:qrcodes")
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
def qr_code_delete_partial(request, short_code):
    """
    Partial view for deleting a QR code.
    """
    etablissement = request.etablissement

    qr_code = get_object_or_404(QRCode, short_code=short_code, etablissement=etablissement)
    qr_code_name = qr_code.name

    if request.method == "POST":
        qr_code.delete()
        messages.success(request, f"Le QR code {qr_code_name} a été supprimé avec succès.")
        return redirect("dashboard:etablissement:qrcodes")

    # GET request - show the form
    context = {
        "qr_code_name": qr_code_name,
        "delete_url": reverse("dashboard:etablissement:qrcode_delete_partial", args=[qr_code.short_code]),
    }

    return starshield_render(
        request,
        "etablissement/qrcodes/delete_partial.html",
        context=context,
    )


@login_required
def qr_code_image_view(request, identifier=None, short_code=None):
    """Generate and return QR code image as PNG."""
    etablissement = get_etablissement_by_identifier(identifier)

    # Get QRCode from short_code path parameter
    qr_code = None

    if short_code:
        try:
            qr_code = QRCode.objects.filter(short_code=short_code, etablissement=etablissement).first()
        except Exception as e:
            logger.debug(
                f"Could not find QRCode with short_code {short_code} for etablissement {etablissement.id}: {e}"
            )

    # If no QRCode found, try first one
    if not qr_code:
        qr_code = etablissement.qr_codes.first()

    # Build redirect URL for QR code - must have short_code
    if qr_code and qr_code.short_code:
        redirect_url = reverse("routing:qr_code_redirect", args=[identifier, qr_code.short_code])
        target_url = request.build_absolute_uri(redirect_url)
    else:
        # Fallback to feedback if no QR code or no short_code
        target_url = request.build_absolute_uri(reverse("reviews:feedback", args=[identifier]))

    # Get customization parameters from query string (for preview) or QRCode
    if qr_code:
        fill_color = request.GET.get("fill_color") or qr_code.qr_fill_color or "#000000"
        fill_color_secondary = request.GET.get("fill_color_secondary") or qr_code.qr_fill_color_secondary or "#000000"
        background_color = request.GET.get("background_color") or qr_code.qr_background_color or "#FFFFFF"
        style = request.GET.get("style") or qr_code.qr_style or "square"
        color_mask = request.GET.get("color_mask") or qr_code.qr_color_mask or "solid"

        # Get logo file if exists
        logo_file = None
        if qr_code.qr_logo:
            try:
                logo_file = qr_code.qr_logo.open()
            except Exception as e:
                logger.debug(f"Could not open QR logo file for QRCode {qr_code.id}: {e}")
                logo_file = None
    else:
        # Fallback to default values if no QRCode exists
        fill_color = request.GET.get("fill_color") or "#000000"
        fill_color_secondary = request.GET.get("fill_color_secondary") or "#000000"
        background_color = request.GET.get("background_color") or "#FFFFFF"
        style = request.GET.get("style") or "square"
        color_mask = request.GET.get("color_mask") or "solid"
        logo_file = None

    # Generate QR code PNG
    try:
        qr_image_bytes = generate_qrcode_png(
            link=target_url,
            fill_color=fill_color,
            fill_color_secondary=fill_color_secondary,
            background_color=background_color,
            style=style,
            color_mask=color_mask,
            logo_file=logo_file,
        )

        return HttpResponse(qr_image_bytes, content_type="image/png")
    except Exception as e:
        logger.error(f"Error generating QR code for etablissement {etablissement.id}: {e}", exc_info=True)
        # Return a simple error response or default QR code
        try:
            qr_image_bytes = generate_qrcode_png(
                link=target_url,
                fill_color="#000000",
                fill_color_secondary="#000000",
                background_color="#FFFFFF",
                style="square",
                color_mask="solid",
            )
            return HttpResponse(qr_image_bytes, content_type="image/png")
        except Exception:
            # If even default fails, return 500
            return HttpResponse("Error generating QR code", status=500)
