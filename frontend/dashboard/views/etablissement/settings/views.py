from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from frontend.dashboard.render import starshield_render
from frontend.reviews.utils import build_feedback_context
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from .forms import ReviewSettingsForm, EtablissementSettingsForm, ThresholdObjectiveForm, QRCodeSettingsForm, RouletteSettingsForm, ROULETTE_ICON_CHOICES
from frontend.roulette.models import RoulettePrize


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = EtablissementSettingsForm(request.POST)
        if form.is_valid():
            etablissement.title = form.cleaned_data["title"]
            etablissement.review_threshold = int(form.cleaned_data["review_threshold"])
            etablissement.target_rating = form.cleaned_data.get("target_rating")
            etablissement.save()

            messages.success(request, "Paramètres mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:settings")
    else:
        form = EtablissementSettingsForm(
            initial={
                "title": etablissement.title,
                "review_threshold": etablissement.review_threshold,
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
def personalisation_settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = ReviewSettingsForm(request.POST)
        if form.is_valid():
            etablissement.review_accent_color = form.cleaned_data["review_accent_color"]
            etablissement.review_show_etablissement_pill = form.cleaned_data["review_show_etablissement_pill"]
            etablissement.review_page_label = form.cleaned_data.get("review_page_label", "")
            etablissement.review_page_text = form.cleaned_data.get("review_page_text", "")
            etablissement.save()

            messages.success(request, "Personalisation mise à jour avec succès.")
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
    preview_context = build_feedback_context(etablissement, identifier, mode="main")

    context = {
        "etablissement": etablissement,
        "form": form,
        "preview_context": preview_context,
    }

    return starshield_render(
        request,
        "etablissement/settings/personalisation.html",
        context=context,
        page_name="personalisation",
    )


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
            return redirect("dashboard:etablissement:settings:threshold")
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
        "etablissement/settings/threshold.html",
        context=context,
        page_name="seuil_et_objectif",
    )


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
            return redirect("dashboard:etablissement:settings:qrcode")

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
            return redirect("dashboard:etablissement:settings:qrcode")
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
        "etablissement/settings/qrcode.html",
        context=context,
        page_name="qr_code",
    )


@google_gmb_connected_required
@selected_etablissement_required
def roulette_settings_view(request):
    etablissement = request.etablissement

    existing_prizes = list(etablissement.roulette_prizes.all())

    if request.method == "POST":
        # Build form with existing prizes data
        prizes_data = existing_prizes if existing_prizes else [None] * 0
        form = RouletteSettingsForm(request.POST, prizes_data=prizes_data)

        if form.is_valid():
            # Update etablissement settings
            etablissement.roulette_enabled = form.cleaned_data.get("roulette_enabled", False)
            etablissement.roulette_spin_cooldown_days = form.cleaned_data["roulette_spin_cooldown_days"]
            etablissement.save()

            # Update or create prizes
            prizes = form.cleaned_data.get("prizes", [])

            # Get existing prize IDs
            existing_ids = {p.id for p in existing_prizes}
            new_ids = {p["id"] for p in prizes if p.get("id")}

            # Delete prizes that were removed
            ids_to_delete = existing_ids - new_ids
            if ids_to_delete:
                RoulettePrize.objects.filter(id__in=ids_to_delete).delete()

            # Update or create prizes
            for prize_data in prizes:
                prize_id = prize_data.get("id")
                if prize_id and RoulettePrize.objects.filter(id=prize_id, etablissement=etablissement).exists():
                    # Update existing prize
                    prize = RoulettePrize.objects.get(id=prize_id)
                    prize.name = prize_data["name"]
                    prize.icon = prize_data["icon"]
                    prize.probability = prize_data["probability"]
                    prize.is_nothing_prize = prize_data["is_nothing"]
                    prize.save()
                else:
                    # Create new prize
                    RoulettePrize.objects.create(
                        etablissement=etablissement,
                        name=prize_data["name"],
                        icon=prize_data["icon"],
                        probability=prize_data["probability"],
                        is_nothing_prize=prize_data["is_nothing"],
                    )

            messages.success(request, "Paramètres de la roue mis à jour avec succès.")
            return redirect("dashboard:etablissement:settings:roulette")
    else:
        # Build initial data
        initial_data = {
            "roulette_enabled": etablissement.roulette_enabled,
            "roulette_spin_cooldown_days": etablissement.roulette_spin_cooldown_days,
        }

        # Add prize data
        for i, prize in enumerate(existing_prizes):
            initial_data[f"prize_{i}_id"] = prize.id
            initial_data[f"prize_{i}_name"] = prize.name
            initial_data[f"prize_{i}_icon"] = prize.icon
            initial_data[f"prize_{i}_probability"] = float(prize.probability)
            initial_data[f"prize_{i}_is_nothing"] = prize.is_nothing_prize

        form = RouletteSettingsForm(initial=initial_data, prizes_data=existing_prizes)

    # Build roulette URL for preview
    identifier = str(etablissement.uuid)
    roulette_url = request.build_absolute_uri(reverse("roulette:wheel", args=[identifier]))

    context = {
        "etablissement": etablissement,
        "form": form,
        "roulette_url": roulette_url,
        "existing_prizes": existing_prizes,
        "icon_choices": ROULETTE_ICON_CHOICES,
    }

    return starshield_render(
        request,
        "etablissement/settings/roulette.html",
        context=context,
        page_name="roulette",
    )
