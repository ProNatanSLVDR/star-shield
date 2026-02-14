from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.private.dashboard.render import starshield_render
from apps.public.roulette.models import RoulettePrize
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import RoulettePrizeForm, RouletteSettingsForm

PRIZE_LIMIT = 8


def _get_or_create_nothing_prize(etablissement):
    """Get or create the automatic 'nothing' prize. Always exists with remaining probability."""
    nothing_prize = etablissement.roulette_prizes.filter(is_nothing_prize=True).first()

    if not nothing_prize:
        # Calculate remaining probability (100% - sum of all other prizes)
        other_prizes_total = sum(
            float(p.probability) for p in etablissement.roulette_prizes.filter(is_nothing_prize=False)
        )
        remaining_probability = max(0, 100 - other_prizes_total)

        nothing_prize = RoulettePrize.objects.create(
            etablissement=etablissement,
            name="Rien",
            icon="fa-solid fa-ban",
            probability=remaining_probability,
            is_nothing_prize=True,
        )

    return nothing_prize


def _update_nothing_prize_probability(etablissement):
    """Update the nothing prize probability to be 100% minus sum of all other prizes."""
    nothing_prize = _get_or_create_nothing_prize(etablissement)
    other_prizes_total = sum(float(p.probability) for p in etablissement.roulette_prizes.filter(is_nothing_prize=False))
    remaining_probability = max(0, 100 - other_prizes_total)
    nothing_prize.probability = remaining_probability
    nothing_prize.save()
    return nothing_prize


def _build_prizes_table_data(etablissement):
    """Build table data structure for prizes (excluding the auto-managed nothing prize)."""
    # Ensure nothing prize exists and is up to date
    nothing_prize = _update_nothing_prize_probability(etablissement)

    # Get all prizes except the nothing prize (which is auto-managed)
    existing_prizes = list(etablissement.roulette_prizes.filter(is_nothing_prize=False))

    # Count includes nothing prize for limit check
    prize_count = len(existing_prizes)  # +1 for nothing prize
    limit_reached = prize_count >= 8

    # Prepare table headers
    headers = [
        {
            "label": "Icône",
            "key": "icon",
            "centered": True,
            "icon": "fa-solid fa-icons",
        },
        {
            "label": "Nom",
            "key": "name",
            "icon": "fa-solid fa-tag",
        },
        {
            "label": "Probabilité",
            "key": "probability",
            "centered": True,
            "orderable": True,
            "icon": "fa-solid fa-percent",
        },
        {
            "label": "Actions",
            "key": "actions",
            "centered": True,
            "icon": "fa-solid fa-gear",
        },
    ]

    # Prepare table rows
    rows = []
    total_probability = 0
    for prize in existing_prizes:
        total_probability += float(prize.probability)

        # Icon cell with HTML
        icon_cell = {
            "type": "html",
            "value": f'<i class="{prize.icon} fa-2x"></i>',
            "centered": True,
        }

        # Action buttons
        buttons = [
            {
                "text": "",
                "icon": "fa-solid fa-pen",
                "classes": "btn-sm btn-primary",
                "extra_kwargs": {
                    "hx_modal_toggle": True,
                    "hx-get": reverse("dashboard:etablissement:roulette:prize_edit", args=[prize.id]),
                },
            },
            {
                "text": "",
                "icon": "fa-solid fa-trash",
                "classes": "btn-sm btn-danger",
                "extra_kwargs": {
                    "hx-confirm": "Êtes-vous certain de vouloir supprimer ce prix ? Cette action est irréversible.",
                    "hx-post": reverse("dashboard:etablissement:roulette:prize_delete", args=[prize.id]),
                    "hx-swap": "none",
                },
            },
        ]

        row = {
            "icon": icon_cell,
            "name": prize.name,
            "probability": f"{float(prize.probability):.2f}%",
            "actions": {
                "type": "buttons",
                "buttons": buttons,
                "centered": True,
            },
        }
        rows.append(row)

    # Add nothing prize as read-only row at the end
    if nothing_prize.probability > 0:
        nothing_icon_cell = {
            "type": "html",
            "value": f'<i class="{nothing_prize.icon} fa-2x"></i>',
            "centered": True,
        }

        nothing_row = {
            "icon": nothing_icon_cell,
            "name": nothing_prize.name,
            "probability": f"{float(nothing_prize.probability):.2f}%",
            "actions": {
                "type": "html",
                "value": (
                    '<span class="text-muted small"><i class="fa-solid fa-info-circle me-1"></i>Géré automatiquement</span>'
                ),
                "centered": True,
            },
        }
        rows.append(nothing_row)

    return {
        "headers": headers,
        "rows": rows,
        "limit_reached": limit_reached,
        "total_probability": total_probability + float(nothing_prize.probability),
        "existing_prizes": existing_prizes,
        "nothing_prize": nothing_prize,
    }


@google_gmb_connected_required
@selected_etablissement_required
def prizes_table_partial(request):
    """HTMX partial view for prizes table."""
    etablissement = request.etablissement

    # Ensure nothing prize exists
    _get_or_create_nothing_prize(etablissement)

    table_data = _build_prizes_table_data(etablissement)

    context = {
        "etablissement": etablissement,
        "prizes_table": {
            "headers": table_data["headers"],
            "rows": table_data["rows"],
        },
        "limit_reached": table_data["limit_reached"],
        "total_probability": table_data["total_probability"],
        "existing_prizes": table_data["existing_prizes"],
    }

    return starshield_render(
        request,
        "etablissement/roulette/prizes_table_partial.html",
        context=context,
    )


@google_gmb_connected_required
@selected_etablissement_required
def roulette_settings_view(request):
    etablissement = request.etablissement

    # Ensure nothing prize exists
    _get_or_create_nothing_prize(etablissement)

    if request.method == "POST":
        form = RouletteSettingsForm(request.POST)

        if form.is_valid():
            # Update etablissement settings
            etablissement.roulette_spin_cooldown_days = form.cleaned_data["roulette_spin_cooldown_days"]
            etablissement.save()

            messages.success(request, "Paramètres de la roue mis à jour avec succès.")
            return redirect("dashboard:etablissement:roulette:roulette")
    else:
        # Build initial data
        initial_data = {
            "roulette_spin_cooldown_days": etablissement.roulette_spin_cooldown_days,
        }
        form = RouletteSettingsForm(initial=initial_data)

    # Build roulette URL for preview
    identifier = str(etablissement.uuid)
    roulette_url = request.build_absolute_uri(reverse("roulette:wheel", args=[identifier]))

    context = {
        "etablissement": etablissement,
        "form": form,
        "roulette_url": roulette_url,
    }

    return starshield_render(
        request,
        "etablissement/roulette/roulette.html",
        context=context,
        page_name="roulette",
    )


@google_gmb_connected_required
@selected_etablissement_required
@require_http_methods(["GET", "POST"])
def prize_create_partial(request):
    """View for creating a new prize (HTMX modal)."""
    etablissement = request.etablissement

    # Check if limit of 8 prizes has been reached (including nothing prize)
    other_prizes_count = etablissement.roulette_prizes.filter(is_nothing_prize=False).count()
    limit_reached = other_prizes_count >= PRIZE_LIMIT

    hx_triggers = {}

    if request.method == "POST":
        if limit_reached:
            form = RoulettePrizeForm(request.POST)
            form.add_error(
                None,
                "Vous avez atteint la limite de 8 prix. Supprimez un prix existant pour en créer un nouveau.",
            )
        else:
            form = RoulettePrizeForm(request.POST)
            if form.is_valid():
                # Ensure nothing prize exists
                _get_or_create_nothing_prize(etablissement)

                new_probability = form.cleaned_data["probability"]

                # Check if adding this prize would leave nothing prize with negative probability
                other_prizes_total = sum(
                    float(p.probability) for p in etablissement.roulette_prizes.filter(is_nothing_prize=False)
                )
                new_other_total = other_prizes_total + float(new_probability)

                if new_other_total > 100:
                    available_probability = 100 - other_prizes_total
                    form.add_error(
                        "probability",
                        (
                            f"La probabilité totale des prix dépasse 100%. "
                            f"Probabilité disponible: {float(available_probability):.2f}%"
                        ),
                    )
                else:
                    # Create the prize (never allow creating nothing prize manually)
                    RoulettePrize.objects.create(
                        etablissement=etablissement,
                        name=form.cleaned_data["name"],
                        icon=form.cleaned_data["icon"],
                        probability=form.cleaned_data["probability"],
                        is_nothing_prize=False,  # Always False for user-created prizes
                    )

                    # Update nothing prize probability
                    _update_nothing_prize_probability(etablissement)

                    messages.success(request, "Prix créé avec succès.")
                    hx_triggers["prizes-updated"] = True
                    hx_triggers["close-modal"] = True
    else:
        form = RoulettePrizeForm()

    # Calculate available probability for info display
    other_prizes_total = sum(float(p.probability) for p in etablissement.roulette_prizes.filter(is_nothing_prize=False))
    available_probability = max(0, 100 - other_prizes_total)

    context = {
        "etablissement": etablissement,
        "form": form,
        "limit_reached": limit_reached,
        "prize_count": other_prizes_count,
        "available_probability": f"{available_probability:.2f}",
    }

    return starshield_render(
        request,
        "etablissement/roulette/prize_create_partial.html",
        context=context,
        hx_triggers=hx_triggers,
    )


@google_gmb_connected_required
@selected_etablissement_required
@require_http_methods(["GET", "POST"])
def prize_edit_partial(request, prize_id):
    """View for editing an existing prize (HTMX modal)."""
    etablissement = request.etablissement
    prize = get_object_or_404(RoulettePrize, id=prize_id, etablissement=etablissement)

    hx_triggers = {}

    # Prevent editing the nothing prize
    if prize.is_nothing_prize:
        messages.error(request, "Le prix 'Rien' est géré automatiquement et ne peut pas être modifié.")
        hx_triggers["close-modal"] = True
    elif request.method == "POST":
        form = RoulettePrizeForm(request.POST)
        if form.is_valid():
            new_probability = form.cleaned_data["probability"]
            old_probability = float(prize.probability)

            # Check if updating this prize would leave nothing prize with negative probability
            other_prizes_total = sum(
                float(p.probability) for p in etablissement.roulette_prizes.filter(is_nothing_prize=False)
            )
            new_other_total = other_prizes_total - old_probability + float(new_probability)

            if new_other_total > 100:
                available_probability = 100 - (other_prizes_total - old_probability)
                form.add_error(
                    "probability",
                    (
                        f"La probabilité totale des prix dépasse 100%. Probabilité disponible: {float(available_probability):.2f}%"
                    ),
                )
            else:
                # Update the prize (never allow setting is_nothing_prize to True manually)
                prize.name = form.cleaned_data["name"]
                prize.icon = form.cleaned_data["icon"]
                prize.probability = form.cleaned_data["probability"]
                prize.is_nothing_prize = False  # Always False for user-edited prizes
                prize.save()

                # Update nothing prize probability
                _update_nothing_prize_probability(etablissement)

                messages.success(request, "Prix modifié avec succès.")
                hx_triggers["prizes-updated"] = True
                hx_triggers["close-modal"] = True
    else:
        form = RoulettePrizeForm(
            initial={
                "name": prize.name,
                "icon": prize.icon,
                "probability": prize.probability,
                "is_nothing_prize": False,  # Never show as checked, users can't create nothing prizes
            }
        )

    # Calculate available probability for info display (include current prize's probability as available)
    other_prizes_total = sum(float(p.probability) for p in etablissement.roulette_prizes.filter(is_nothing_prize=False))
    available_probability = max(0, 100 - (other_prizes_total - float(prize.probability)))

    context = {
        "etablissement": etablissement,
        "form": form,
        "prize": prize,
        "available_probability": f"{available_probability:.2f}",
    }

    return starshield_render(
        request,
        "etablissement/roulette/prize_edit_partial.html",
        context=context,
        hx_triggers=hx_triggers,
    )


@google_gmb_connected_required
@selected_etablissement_required
@require_POST
def prize_delete_partial(request, prize_id):
    """View for deleting a prize (HTMX modal)."""
    etablissement = request.etablissement
    prize = get_object_or_404(RoulettePrize, id=prize_id, etablissement=etablissement)

    hx_triggers = {}

    # Prevent deleting the nothing prize
    if prize.is_nothing_prize:
        messages.error(request, "Le prix 'Rien' est géré automatiquement et ne peut pas être supprimé.")
        hx_triggers["close-modal"] = True
    else:
        # Delete the prize
        prize.delete()

        # Update nothing prize probability (it will increase by the deleted prize's probability)
        _update_nothing_prize_probability(etablissement)

        messages.success(request, f"Le prix {prize.name} a été supprimé avec succès.")
        hx_triggers["prizes-updated"] = True
        hx_triggers["close-modal"] = True

    return starshield_render(
        request,
        hx_triggers=hx_triggers,
    )
