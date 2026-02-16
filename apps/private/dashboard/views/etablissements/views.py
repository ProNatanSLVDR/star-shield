from datetime import datetime

import stripe
from allauth.account.decorators import reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST

from apps.private.auths.models import Etablissement
from apps.private.dashboard.render import starshield_render
from apps.private.dashboard.views.etablissement.settings.forms import EtablissementSettingsForm
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

stripe.api_key = settings.STRIPE_SECRET_KEY


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
        subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
        if not subscription:
            subscription_badge = {
                "type": "badge",
                "value": "Non abonné",
                "variant": "danger",
                "icon": "fa-solid fa-circle-xmark",
                "tooltip": "Cliquez sur 'Gérer' pour souscrire à un abonnement",
            }
        elif subscription.cancel_at_period_end:
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
    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    is_cancelled_at_period_end = subscription and subscription.cancel_at_period_end

    if is_cancelled_at_period_end:
        subscription_state = "cancellation_pending"
    elif subscription and etablissement.active:
        subscription_state = "active"
    else:
        subscription_state = "inactive"

    # Determine plan label from price_id
    plan_label = ""
    if subscription and subscription.price_id:
        price_map = settings.STRIPE_PRODUCTS.get("basic_subscription", {})
        if subscription.price_id == price_map.get("monthly"):
            plan_label = "Mensuel"
        elif subscription.price_id == price_map.get("trimestrial"):
            plan_label = "Trimestriel"
        elif subscription.price_id == price_map.get("yearly"):
            plan_label = "Annuel"

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
            price_map = settings.STRIPE_PRODUCTS.get("basic_subscription", {})
            if pending_price_id == price_map.get("monthly"):
                pending_plan_label = "Mensuel"
            elif pending_price_id == price_map.get("trimestrial"):
                pending_plan_label = "Trimestriel"
            elif pending_price_id == price_map.get("yearly"):
                pending_plan_label = "Annuel"

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
    has_credential = hasattr(request.user, "google_credential") and request.user.google_credential is not None

    if not has_credential:
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
    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    is_reactivation = subscription is not None and subscription.cancel_at_period_end
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
                from datetime import datetime

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
        monthly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("monthly")
        trimestrial_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("trimestrial")
        yearly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("yearly")

        monthly_price_data = None
        trimestrial_price_data = None
        yearly_price_data = None

        if monthly_price_id:
            try:
                monthly_price = stripe.Price.retrieve(monthly_price_id)
                monthly_price_data = {
                    "id": monthly_price_id,
                    "amount": monthly_price.unit_amount / 100 if monthly_price.unit_amount else 0,
                    "currency": (monthly_price.currency or "eur").upper(),
                }
            except Exception as e:
                logger.error(f"Error fetching monthly price from Stripe: {e}")

        if trimestrial_price_id:
            try:
                trimestrial_price = stripe.Price.retrieve(trimestrial_price_id)
                trimestrial_price_data = {
                    "id": trimestrial_price_id,
                    "amount": trimestrial_price.unit_amount / 100 if trimestrial_price.unit_amount else 0,
                    "currency": (trimestrial_price.currency or "eur").upper(),
                }
            except Exception as e:
                logger.error(f"Error fetching trimestrial price from Stripe: {e}")

        if yearly_price_id:
            try:
                yearly_price = stripe.Price.retrieve(yearly_price_id)
                yearly_price_data = {
                    "id": yearly_price_id,
                    "amount": yearly_price.unit_amount / 100 if yearly_price.unit_amount else 0,
                    "currency": (yearly_price.currency or "eur").upper(),
                }
            except Exception as e:
                logger.error(f"Error fetching yearly price from Stripe: {e}")

        # Calculate full price (without discount) and savings percentage for trimestrial and yearly plans
        if monthly_price_data and trimestrial_price_data:
            full_price = monthly_price_data["amount"] * 3
            if full_price > trimestrial_price_data["amount"]:
                trimestrial_price_data["full_price"] = full_price
                trimestrial_price_data["savings_percent"] = int(
                    (full_price - trimestrial_price_data["amount"]) / full_price * 100
                )

        if monthly_price_data and yearly_price_data:
            full_price = monthly_price_data["amount"] * 12
            if full_price > yearly_price_data["amount"]:
                yearly_price_data["full_price"] = full_price
                yearly_price_data["savings_percent"] = int(
                    (full_price - yearly_price_data["amount"]) / full_price * 100
                )

        context["monthly_price"] = monthly_price_data
        context["trimestrial_price"] = trimestrial_price_data
        context["yearly_price"] = yearly_price_data

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

    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    is_reactivation = subscription is not None and subscription.cancel_at_period_end
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

    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    if not subscription or subscription.cancel_at_period_end:
        messages.error(request, "Aucun abonnement actif trouvé pour cet établissement.")
        return starshield_render(request, "etablissements/change_plan_partial.html", context={})

    current_price_id = subscription.price_id

    # Check for pending plan change
    stripe_subscription = check_existing_subscription_for_etablissement(request.user, etablissement.id)
    pending_price_id = None
    if stripe_subscription:
        pending_price_id = get_pending_plan_change(stripe_subscription["id"], request.user.stripe_customer_id)

    # Fetch prices from Stripe
    monthly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("monthly")
    trimestrial_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("trimestrial")
    yearly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("yearly")

    prices = []
    for label, price_id, icon, period_label in [
        ("Mensuel", monthly_price_id, "fa-solid fa-calendar-day", "/mois"),
        ("Trimestriel", trimestrial_price_id, "fa-solid fa-calendar-week", "/trimestre"),
        ("Annuel", yearly_price_id, "fa-solid fa-calendar", "/an"),
    ]:
        if not price_id:
            continue
        try:
            stripe_price = stripe.Price.retrieve(price_id)
            price_data = {
                "id": price_id,
                "label": label,
                "icon": icon,
                "period_label": period_label,
                "amount": stripe_price.unit_amount / 100 if stripe_price.unit_amount else 0,
                "currency": (stripe_price.currency or "eur").upper(),
                "is_current": price_id == current_price_id,
                "is_pending": price_id == pending_price_id,
            }
            prices.append(price_data)
        except Exception as e:
            logger.error(f"Error fetching price {price_id} from Stripe: {e}")

    # Calculate savings relative to monthly
    monthly_amount = next((p["amount"] for p in prices if p["label"] == "Mensuel"), None)
    if monthly_amount:
        for price_data in prices:
            if price_data["label"] == "Trimestriel":
                full_price = monthly_amount * 3
                if full_price > price_data["amount"]:
                    price_data["full_price"] = full_price
                    price_data["savings_percent"] = int((full_price - price_data["amount"]) / full_price * 100)
            elif price_data["label"] == "Annuel":
                full_price = monthly_amount * 12
                if full_price > price_data["amount"]:
                    price_data["full_price"] = full_price
                    price_data["savings_percent"] = int((full_price - price_data["amount"]) / full_price * 100)

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
