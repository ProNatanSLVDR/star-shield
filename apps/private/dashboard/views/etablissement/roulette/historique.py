from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.private.dashboard.render import starshield_render
from apps.public.roulette.models import RouletteAnalytics, RouletteSpin
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)


@google_gmb_connected_required
@selected_etablissement_required
def historique_view(request):
    return starshield_render(
        request,
        "etablissement/roulette/historique.html",
        page_name="roulette_historique",
    )


@google_gmb_connected_required
@selected_etablissement_required
def historique_content_partial(request):
    etablissement = request.etablissement
    period = request.GET.get("period", "30")

    # Build date filter
    now = timezone.now()
    date_filter = {}
    if period != "all":
        try:
            days = int(period)
        except ValueError:
            days = 30
        date_filter["created_at__gte"] = now - timedelta(days=days)

    # Query spins (won prizes) for this establishment
    spins_qs = RouletteSpin.objects.filter(
        etablissement=etablissement,
        **date_filter,
    )

    # Stats
    prizes_given = spins_qs.count()
    spins_played = RouletteAnalytics.objects.filter(
        etablissement=etablissement,
        type="roulette_spun",
        **date_filter,
    ).count()
    prizes_redeemed = spins_qs.filter(is_used=True).count()

    if prizes_given > 0:
        redemption_rate = round((prizes_redeemed / prizes_given) * 100, 1)
    else:
        redemption_rate = 0

    stats = [
        {
            "label": "Tours joués",
            "value": spins_played,
            "icon": "fa-solid fa-rotate",
            "color": "purple",
            "bg": "rgba(111, 66, 193, 0.1)",
        },
        {
            "label": "Prix distribués",
            "value": prizes_given,
            "icon": "fa-solid fa-gift",
            "color": "primary",
            "bg": "rgba(13, 110, 253, 0.1)",
        },
        {
            "label": "Prix réclamés",
            "value": prizes_redeemed,
            "icon": "fa-solid fa-check",
            "color": "success",
            "bg": "rgba(25, 135, 84, 0.1)",
        },
        {
            "label": "Taux de réclamation",
            "value": f"{redemption_rate}%",
            "icon": "fa-solid fa-percent",
            "color": "warning",
            "bg": "rgba(255, 193, 7, 0.1)",
        },
    ]

    # Build table data
    headers = [
        {
            "label": "Prix",
            "key": "prize_name",
            "searchable": True,
            "icon": "fa-solid fa-gift",
        },
        {
            "label": "Code",
            "key": "code",
            "icon": "fa-solid fa-barcode",
        },
        {
            "label": "Date",
            "key": "date",
            "orderable": True,
            "icon": "fa-solid fa-calendar",
        },
        {
            "label": "Statut",
            "key": "status",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-circle-info",
        },
        {
            "label": "Actions",
            "key": "actions",
            "centered": True,
            "icon": "fa-solid fa-bolt",
        },
    ]

    rows = []
    for spin in spins_qs:
        toggle_url = reverse("dashboard:etablissement:roulette:toggle_spin_status", args=[spin.id])

        if spin.is_used:
            status_html = '<span class="badge bg-success"><i class="fa-solid fa-check me-1"></i>Réclamé</span>'
            action_html = (
                f'<button class="btn btn-sm btn-outline-primary" '
                f'hx-post="{toggle_url}" hx-swap="none" '
                f'hx-confirm="Voulez-vous marquer ce prix comme non réclamé ?" '
                f'title="Marquer en attente">'
                f'<i class="fa-solid fa-clock me-1"></i>Marquer comme non réclamé</button>'
            )
        else:
            status_html = '<span class="badge bg-warning"><i class="fa-solid fa-clock me-1"></i>En attente</span>'
            action_html = (
                f'<button class="btn btn-sm btn-outline-primary" '
                f'hx-post="{toggle_url}" hx-swap="none" '
                f'hx-confirm="Voulez-vous marquer ce prix comme réclamé ?" '
                f'title="Marquer réclamé">'
                f'<i class="fa-solid fa-check me-1"></i>Marquer comme réclamé</button>'
            )

        rows.append(
            {
                "prize_name": {
                    "type": "html",
                    "value": f'<i class="{spin.prize_icon} me-2"></i>{spin.prize_name}',
                },
                "code": spin.prize_code,
                "date": {
                    "value": spin.created_at.strftime("%d/%m/%Y %H:%M"),
                    "sort_value": spin.created_at.timestamp(),
                },
                "status": {
                    "type": "html",
                    "value": status_html,
                    "sort_value": 1 if spin.is_used else 0,
                    "centered": True,
                },
                "actions": {
                    "type": "html",
                    "value": action_html,
                    "centered": True,
                },
            }
        )

    context = {
        "stats": stats,
        "table_data": {
            "headers": headers,
            "rows": rows,
        },
        "current_period": period,
    }

    return starshield_render(
        request,
        "etablissement/roulette/historique_content_partial.html",
        context=context,
    )


@google_gmb_connected_required
@selected_etablissement_required
@require_POST
def toggle_spin_status(request, spin_id):
    """HTMX endpoint to toggle a spin's is_used status."""
    etablissement = request.etablissement
    spin = get_object_or_404(RouletteSpin, id=spin_id, etablissement=etablissement)
    spin.is_used = not spin.is_used
    spin.save(update_fields=["is_used"])

    return starshield_render(
        request,
        hx_triggers={"historique-updated": True},
    )
