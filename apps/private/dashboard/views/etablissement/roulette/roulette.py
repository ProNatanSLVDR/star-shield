from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from apps.private.dashboard.render import starshield_render
from apps.public.roulette.models import RoulettePrize
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import ROULETTE_ICON_CHOICES, RouletteSettingsForm


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
            return redirect("dashboard:etablissement:roulette:roulette")
    else:
        # Build initial data
        initial_data = {
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
        "etablissement/roulette/roulette.html",
        context=context,
        page_name="roulette",
    )
