from datetime import datetime

from allauth.account.decorators import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST

from apps.private.auths.models import Etablissement
from apps.private.dashboard.render import starshield_render
from apps.private.dashboard.views.etablissement.settings.forms import EtablissementSettingsForm
from apps.private.payments.helpers import get_plan_label, get_stripe_prices, get_subscription_state
from apps.private.payments.services import (
    cancel_subscription_for_etablissement,
    change_plan_for_etablissement,
    check_existing_subscription_for_etablissement,
    get_pending_plan_change,
    reactivate_subscription_for_etablissement,
    sync_stripe_data,
)
from starshield.decorators import google_gmb_connected_required, unselect_etablissement
from starshield.logger import logger

from .forms import ImportEtablissementForm, ToggleEtablissementStatusForm


@google_gmb_connected_required
@unselect_etablissement
def list_etablissements_view(request):
    if not request.htmx:
        return starshield_render(request, "etablissements/list.html", page_name="etablissements")

    etablissements = request.user.google_credential.etablissements.all()

    # Prepare table headers
    headers = [
        {
            "label": "Nom de l'établissement",
            "key": "title",
            "searchable": True,
            "orderable": True,
            "icon": "fa-solid fa-building",
        },
        {
            "label": "Date de création",
            "key": "created_at",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-calendar",
        },
        {
            "label": "Fonctionnalités",
            "key": "features",
            "centered": True,
            "icon": "fa-solid fa-toggle-on",
        },
        {
            "label": "Abonnement",
            "key": "subscription",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-credit-card",
        },
        {
            "label": "Gérer (abonnement, etc.)",
            "key": "actions",
            "centered": True,
            "icon": "fa-solid fa-gear",
        },
    ]

    # Prepare table rows
    rows = []
    for etablissement in etablissements:
        # Subscription status logic
        sub_info = get_subscription_state(etablissement)
        state = sub_info["state"]
        if state == "inactive":
            subscription_badge = {
                "type": "badge",
                "value": "Non abonné",
                "variant": "danger",
                "icon": "fa-solid fa-circle-xmark",
                "tooltip": "Cliquez sur 'Gérer' pour souscrire à un abonnement",
            }
        elif state == "cancellation_pending":
            subscription_badge = {
                "type": "badge",
                "value": "Abonné (annulation)",
                "variant": "warning",
                "icon": "fa-solid fa-clock",
                "tooltip": "L'abonnement sera annulé à la fin de la période en cours",
            }
        else:
            subscription_badge = {
                "type": "badge",
                "value": "Abonné",
                "variant": "success",
                "icon": "fa-solid fa-check-circle",
                "tooltip": "L'abonnement est actif, merci de votre fidélité !",
            }

        # Date formatting with tooltip
        created_at_str = etablissement.created_at.strftime("%d/%m/%Y") if etablissement.created_at else "N/A"
        created_at_full = etablissement.created_at.strftime("%d/%m/%Y à %H:%M") if etablissement.created_at else "N/A"
        created_at_cell = (
            {
                "type": "text",
                "value": created_at_str,
                "tooltip": created_at_full if etablissement.created_at else None,
            }
            if etablissement.created_at
            else created_at_str
        )

        # Feature badges (fused icon group with tooltips)
        features = [
            ("Filtrage", etablissement.review_filtering_enabled and etablissement.active, "fa-solid fa-filter"),
            ("Roulette", etablissement.roulette_enabled and etablissement.active, "fa-solid fa-record-vinyl"),
            ("IA", etablissement.ai_responses_enabled and etablissement.active, "fa-solid fa-robot"),
        ]
        feature_badges = []
        for label, enabled, icon in features:
            if enabled:
                classes = "badge bg-success text-white"
            else:
                classes = "badge bg-body-secondary text-muted"
            feature_badges.append(
                f'<span class="{classes}" data-bs-toggle="tooltip" data-bs-title="{label}">'
                f'<i class="{icon}"></i></span>'
            )
        features_html = '<span class="feature-group">' + "".join(feature_badges) + "</span>"

        details_url = reverse("dashboard:etablissements:details_partial", args=[etablissement.id])
        manage_button = {
            "text": "Gérer",
            "icon": "fa-solid fa-gear",
            "classes": "btn-sm btn-outline-primary w-100",
            "extra_kwargs": {
                "hx-get": details_url,
                "hx-target": "#detailsModal-inner-content",
                "hx-swap": "innerHTML",
                "data-bs-toggle": "modal",
                "data-bs-target": "#detailsModal",
            },
        }

        row = {
            "title": etablissement.title,
            "created_at": created_at_cell,
            "subscription": subscription_badge,
            "features": {"type": "html", "value": features_html},
            "actions": {
                "type": "buttons",
                "buttons": [manage_button],
                "centered": True,
            },
        }
        rows.append(row)

    # Prepare context with table data
    context = {
        "etablissements_table": {
            "headers": headers,
            "rows": rows,
        }
    }
    return starshield_render(
        request,
        "etablissements/list_partial.html",
        context=context,
        page_name="etablissements",
    )


@google_gmb_connected_required
@require_http_methods(["GET", "POST"])
def etablissement_details_partial(request, id):
    """
    Show establishment details modal with subscription status, settings form, and actions.
    On POST: save settings (title, target_rating) and re-render the modal.
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)
    # Determine subscription state
    sub_info = get_subscription_state(etablissement)
    subscription = sub_info["subscription"]
    subscription_state = sub_info["state"]

    # Determine plan label from price_id
    plan_label = get_plan_label(subscription.price_id if subscription else None)

    # Fetch subscription details from Stripe
    stripe_subscription = None
    if subscription:
        try:
            stripe_subscription = check_existing_subscription_for_etablissement(request.user, etablissement.id)
        except Exception as e:
            logger.error(f"Error fetching subscription for etablissement {etablissement.id}: {e}")

    # Settings form (POST = save, GET = prefill)
    hx_triggers = {}
    if request.method == "POST":
        settings_form = EtablissementSettingsForm(request.POST)
        if settings_form.is_valid():
            etablissement.title = settings_form.cleaned_data["title"]
            etablissement.target_rating = settings_form.cleaned_data.get("target_rating")
            etablissement.save(update_fields=["title", "target_rating"])
            messages.success(request, "Paramètres mis à jour avec succès.")
            hx_triggers["etablissements-updated"] = True
            # Re-populate form with saved values
            settings_form = EtablissementSettingsForm(
                initial={"title": etablissement.title, "target_rating": etablissement.target_rating}
            )
    else:
        settings_form = EtablissementSettingsForm(
            initial={"title": etablissement.title, "target_rating": etablissement.target_rating}
        )

    # Check for pending plan change
    pending_plan_label = ""
    if stripe_subscription:
        pending_price_id = get_pending_plan_change(stripe_subscription["id"], request.user.stripe_customer_id)
        if pending_price_id:
            pending_plan_label = get_plan_label(pending_price_id)

    # Build subscription_data for template
    subscription_data = {
        "plan_label": plan_label,
        "pending_plan_label": pending_plan_label,
        "status": subscription_state,
        "price": None,
        "currency": "",
        "current_period_start": None,
        "current_period_end": None,
        "created": None,
    }

    if stripe_subscription:
        plan = stripe_subscription.get("plan") or {}
        items_data = (stripe_subscription.get("items", {}).get("data") or [{}])[0]

        if plan.get("amount") is not None:
            subscription_data["price"] = plan["amount"] / 100
        subscription_data["currency"] = plan.get("currency", "eur")

        if items_data.get("current_period_start"):
            subscription_data["current_period_start"] = datetime.fromtimestamp(items_data["current_period_start"])
        if items_data.get("current_period_end"):
            subscription_data["current_period_end"] = datetime.fromtimestamp(items_data["current_period_end"])
        if items_data.get("created"):
            subscription_data["created"] = datetime.fromtimestamp(items_data["created"])

    details_url = reverse("dashboard:etablissements:details_partial", args=[etablissement.id])
    context = {
        "etablissement": etablissement,
        "subscription_data": subscription_data,
        "settings_form": settings_form,
        "details_url": details_url,
        "toggle_status_url": reverse("dashboard:etablissements:toggle_status_partial", args=[etablissement.id]),
        "change_plan_url": reverse("dashboard:etablissements:change_plan_partial", args=[etablissement.id]),
        "delete_url": reverse("dashboard:etablissements:delete_partial", args=[etablissement.id]),
    }

    return starshield_render(request, "etablissements/details_partial.html", context=context, hx_triggers=hx_triggers)


@google_gmb_connected_required
@require_http_methods(["GET", "POST"])
def import_etablissement_partial(request):
    hx_triggers = {}

    if request.method == "POST":
        available_locations = request.session.get("available_locations", [])
        form = ImportEtablissementForm(request.POST, available_locations=available_locations)

        if form.is_valid():
            selected_locations = form.cleaned_data.get("locations", [])
            google_credential = request.user.google_credential

            # Create a dictionary for easy lookup
            locations_dict = {loc["name"]: loc for loc in available_locations}

            # Import each selected location
            for location_name in selected_locations:
                location = locations_dict.get(location_name)
                if location:
                    google_credential.create_etablissement_from_location(
                        account_id=location["account_id"], location_id=location_name
                    )

            messages.success(request, "Établissements importés avec succès!")
            hx_triggers["etablissements-updated"] = True
            hx_triggers["close-modal"] = True
    else:
        available_locations = request.user.google_credential.list_available_locations()
        request.session["available_locations"] = available_locations
        form = ImportEtablissementForm(available_locations=available_locations)

    # Count imported établissements
    imported_count = sum(1 for location in available_locations if location.get("exists", False))
    selectable_count = len(available_locations) - imported_count

    context = {
        "form": form,
        "available_locations": available_locations,
        "imported_count": imported_count,
        "selectable_count": selectable_count,
    }
    return starshield_render(
        request,
        "etablissements/add_partial.html",
        context=context,
        hx_triggers=hx_triggers,
    )


@google_gmb_connected_required
@require_http_methods(["GET", "POST"])
def delete_etablissement_confirmation_partial(request, id):
    """
    Pour supprimer un etablissement
    Double confirmation la suppression (modal + hx-confirm)
    Safety check: block deletion of active etablissements (button is disabled in UI)
    """

    # on essaye de récupérer l'établissement
    etablissement = Etablissement.objects.filter(id=id, google_credential=request.user.google_credential).first()

    hx_triggers = {}
    context = {
        "etablissement_title": None,
        "delete_url": None,
    }

    if etablissement:
        # Safety check: prevent deletion of active etablissements
        if etablissement.active:
            messages.error(request, "Vous devez d'abord désactiver l'établissement avant de le supprimer.")
            hx_triggers["etablissements-updated"] = True
            hx_triggers["close-modal"] = True
        else:
            context["etablissement_title"] = etablissement.title
            context["delete_url"] = reverse("dashboard:etablissements:delete_partial", args=[etablissement.id])

            if request.method == "POST":
                etablissement.delete()
                messages.success(request, f"L'établissement {etablissement.title} a été supprimé.")
                hx_triggers["etablissements-updated"] = True
                hx_triggers["close-modal"] = True
    else:
        messages.error(request, "Établissement non trouvé.")
        hx_triggers["etablissements-updated"] = True
        hx_triggers["close-modal"] = True

    return starshield_render(
        request,
        "etablissements/delete_partial.html",
        context=context,
        hx_triggers=hx_triggers,
    )


@google_gmb_connected_required
def select_etablissement(request, id):
    etablissement = Etablissement.objects.filter(id=id, google_credential=request.user.google_credential).first()

    if etablissement:
        request.session["selected_etablissement"] = etablissement.id
        return redirect("dashboard:etablissement:overview")
    messages.error(request, "Établissement non trouvé.")
    return redirect("dashboard:etablissements:list")


@google_gmb_connected_required
def unselect_etablissement(request):
    """
    Unselects the currently selected établissement by clearing the session variable.
    """
    if "selected_etablissement" in request.session:
        del request.session["selected_etablissement"]

    return redirect("dashboard:accueil")


def etablissement_selector_partial(request):
    """
    Returns the établissement selector partial for the sidebar.
    Only loaded on demand via HTMX.
    Handles invalid credentials gracefully by showing an error message.
    """
    # Check credential validity without using decorator to avoid redirect
    if not request.user.has_google_credential:
        context = {
            "error": True,
            "error_message": "Aucun compte Google My Business n'est connecté.",
            "reconnect_url": reverse("dashboard:onboarding:reconnect_google"),
        }
        return starshield_render(request, "etablissements/selector_partial.html", context=context)

    google_credential = request.user.google_credential

    if not google_credential.is_valid or google_credential.has_invalid_grants:
        reason = "invalid_grants" if google_credential.has_invalid_grants else "expired"
        context = {
            "error": True,
            "error_message": "Votre connexion Google My Business a expiré ou a été révoquée.",
            "reconnect_url": reverse("dashboard:onboarding:reconnect_google"),
            "reason": reason,
        }
        return starshield_render(request, "etablissements/selector_partial.html", context=context)

    etablissements = request.user.google_credential.etablissements.all()

    # Prepare table headers
    headers = [
        {
            "label": "Nom de l'établissement",
            "key": "title",
            "searchable": True,
            "orderable": True,
        },
        {
            "label": "Statut",
            "key": "status",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-circle-check",
        },
        {"label": "Actions", "key": "actions", "centered": True},
    ]

    # Prepare table rows
    rows = []
    for etablissement in etablissements:
        select_button = {
            "text": "Sélectionner",
            "icon": "fa-solid fa-right-to-bracket",
            "classes": "btn-sm btn-primary",
            "extra_kwargs": {
                "href": reverse("dashboard:etablissements:select", args=[etablissement.id]),
            },
        }

        status_badge = {
            "type": "badge",
            "value": "Actif" if etablissement.active else "Inactif",
            "variant": "success" if etablissement.active else "warning",
        }

        row = {
            "title": etablissement.title,
            "status": status_badge,
            "actions": {
                "type": "buttons",
                "buttons": [select_button],
                "centered": True,
            },
        }
        rows.append(row)

    # Prepare context with table data
    context = {
        "etablissements_table": {
            "headers": headers,
            "rows": rows,
        }
    }

    return starshield_render(request, "etablissements/selector_partial.html", context=context)


@google_gmb_connected_required
def toggle_etablissement_status_partial(request, id):
    """
    Show toggle status modal (activate/deactivate/reactivate) with billing explanation.
    For activation: shows price selection if no subscription, or confirmation if subscription exists.
    For deactivation: shows confirmation explaining subscription continues until period end.
    For reactivation: shows confirmation explaining subscription will continue normally.
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)

    # Check subscription status first to determine reactivation
    sub_info = get_subscription_state(etablissement)
    subscription = sub_info["subscription"]
    is_reactivation = sub_info["state"] == "cancellation_pending"
    is_activation = not etablissement.active and not is_reactivation

    context = {
        "etablissement": etablissement,
        "is_activation": is_activation,
        "is_reactivation": is_reactivation,
        "toggle_url": reverse("dashboard:etablissements:toggle_status", args=[etablissement.id]),
        "checkout_url": reverse("payments:create_checkout_session"),
    }

    # Check if establishment has an active subscription
    has_active_subscription = etablissement.has_active_subscription()
    context["has_active_subscription"] = has_active_subscription

    # Fetch period end date from Stripe if subscription exists
    period_end_date = None
    period_end_date_formatted = None
    if subscription or has_active_subscription:
        try:
            stripe_subscription = check_existing_subscription_for_etablissement(request.user, etablissement.id)
            if stripe_subscription and stripe_subscription.get("current_period_end"):
                period_end_timestamp = stripe_subscription["current_period_end"]
                period_end_date = datetime.fromtimestamp(period_end_timestamp)
                # Format date in French
                french_months = {
                    1: "janvier",
                    2: "février",
                    3: "mars",
                    4: "avril",
                    5: "mai",
                    6: "juin",
                    7: "juillet",
                    8: "août",
                    9: "septembre",
                    10: "octobre",
                    11: "novembre",
                    12: "décembre",
                }
                month_name = french_months.get(period_end_date.month, period_end_date.strftime("%B"))
                period_end_date_formatted = f"{period_end_date.day} {month_name} {period_end_date.year}"
        except Exception as e:
            logger.error(f"Error fetching period end date for etablissement {etablissement.id}: {e}")

    context["period_end_date"] = period_end_date
    context["period_end_date_formatted"] = period_end_date_formatted

    # For activation: if no subscription, fetch price options
    if is_activation and not has_active_subscription:
        prices = get_stripe_prices()
        context["monthly_price"] = prices["monthly"]
        context["trimestrial_price"] = prices["trimestrial"]
        context["yearly_price"] = prices["yearly"]

    return starshield_render(
        request,
        "etablissements/toggle_status_partial.html",
        context=context,
    )


@google_gmb_connected_required
@require_POST
def toggle_etablissement_status(request, id):
    """
    Toggle establishment status (activate/deactivate/reactivate).
    For activation: if no subscription, redirects to checkout. If subscription exists, activates establishment.
    For deactivation: sets active=False (subscription continues until period end).
    For reactivation: removes cancel_at_period_end flag from subscription.
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)

    sub_info = get_subscription_state(etablissement)
    is_reactivation = sub_info["state"] == "cancellation_pending"
    is_activation = not etablissement.active and not is_reactivation

    try:
        if is_activation:
            if etablissement.has_active_subscription():
                sync_stripe_data(request.user)
            else:
                form = ToggleEtablissementStatusForm(request.POST)
                if form.is_valid():
                    request.session["price_id"] = form.cleaned_data["price_id"]
                    request.session["etablissement_id"] = etablissement.id
                    checkout_url = reverse("payments:create_checkout_session")
                    if request.htmx:
                        response = HttpResponse()
                        response["HX-Redirect"] = checkout_url
                        return response
                    return redirect(checkout_url)
                logger.debug(f"ToggleEtablissementStatusForm errors: {form.errors}")
                messages.error(request, "Une erreur est survenue lors de la sélection du plan d'abonnement.")

        elif is_reactivation:
            reactivated = reactivate_subscription_for_etablissement(request.user, etablissement.id)
            if reactivated:
                sync_stripe_data(request.user)
                messages.success(request, "L'abonnement a été réactivé avec succès.")
            else:
                messages.error(request, "Impossible de réactiver l'abonnement.")

        elif etablissement.has_active_subscription():
            cancel_subscription_for_etablissement(request.user, etablissement.id)
            sync_stripe_data(request.user)
            messages.success(request, "L'abonnement a été annulé.")
        else:
            messages.success(request, f"L'établissement {etablissement.title} a été désactivé.")

    except Exception as e:
        logger.error(f"Error toggling etablissement {etablissement.id} status: {e}")
        messages.error(request, "Une erreur est survenue.")

    redirect_url = reverse("dashboard:etablissements:list")
    if request.htmx:
        response = HttpResponse()
        response["HX-Redirect"] = redirect_url
        return response
    return redirect(redirect_url)


@google_gmb_connected_required
def change_plan_partial(request, id):
    """
    Show change plan modal with price selection (current plan disabled).
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)

    sub_info = get_subscription_state(etablissement)
    subscription = sub_info["subscription"]
    if not subscription or sub_info["state"] == "cancellation_pending":
        messages.error(request, "Aucun abonnement actif trouvé pour cet établissement.")
        return starshield_render(request, "etablissements/change_plan_partial.html", context={})

    current_price_id = subscription.price_id

    # Check for pending plan change
    stripe_subscription = check_existing_subscription_for_etablissement(request.user, etablissement.id)
    pending_price_id = None
    if stripe_subscription:
        pending_price_id = get_pending_plan_change(stripe_subscription["id"], request.user.stripe_customer_id)

    # Fetch prices from Stripe
    stripe_prices = get_stripe_prices()
    prices = []
    for label, key, icon, period_label in [
        ("Mensuel", "monthly", "fa-solid fa-calendar-day", "/mois"),
        ("Trimestriel", "trimestrial", "fa-solid fa-calendar-week", "/trimestre"),
        ("Annuel", "yearly", "fa-solid fa-calendar", "/an"),
    ]:
        price_data = stripe_prices.get(key)
        if not price_data:
            continue
        price_data["label"] = label
        price_data["icon"] = icon
        price_data["period_label"] = period_label
        price_data["is_current"] = price_data["id"] == current_price_id
        price_data["is_pending"] = price_data["id"] == pending_price_id
        prices.append(price_data)

    context = {
        "etablissement": etablissement,
        "prices": prices,
        "has_pending_change": pending_price_id is not None,
        "change_plan_url": reverse("dashboard:etablissements:change_plan", args=[etablissement.id]),
    }

    return starshield_render(request, "etablissements/change_plan_partial.html", context=context)


@google_gmb_connected_required
@require_POST
def change_plan(request, id):
    """
    Process the plan change for an etablissement.
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)

    form = ToggleEtablissementStatusForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Le plan d'abonnement sélectionné n'est pas valide.")
    else:
        new_price_id = form.cleaned_data["price_id"]
        try:
            result = change_plan_for_etablissement(request.user, etablissement.id, new_price_id)
            if result == "cancelled":
                messages.success(request, "Le changement de plan programmé a été annulé.")
            elif result:
                sync_stripe_data(request.user)
                messages.success(
                    request,
                    "Le changement de plan prendra effet à la fin de votre période de facturation en cours.",
                )
            else:
                messages.error(request, "Impossible de modifier le plan d'abonnement.")
        except Exception as e:
            logger.error(f"Error changing plan for etablissement {etablissement.id}: {e}")
            messages.error(request, "Une erreur est survenue lors du changement de plan.")

    redirect_url = reverse("dashboard:etablissements:list")
    if request.htmx:
        response = HttpResponse()
        response["HX-Redirect"] = redirect_url
        return response
    return redirect(redirect_url)
