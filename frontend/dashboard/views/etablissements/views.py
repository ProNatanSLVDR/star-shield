from allauth.account.decorators import reverse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from auths.models import Etablissement
from starshield.decorators import google_gmb_connected_required
from frontend.dashboard.render import starshield_render
from django.contrib import messages
from .forms import ImportEtablissementForm, ToggleEtablissementStatusForm
from payments.services import sync_stripe_data, cancel_subscription_for_etablissement, reactivate_subscription_for_etablissement, check_existing_subscription_for_etablissement
import logging
import stripe
from django.conf import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@google_gmb_connected_required
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
            "label": "Abonnement",
            "key": "subscription",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-credit-card",
        },
        {"label": "Actions", "key": "actions", "centered": True, "icon": "fa-solid fa-gear"},
    ]

    # Prepare table rows
    rows = []
    for etablissement in etablissements:
        buttons = []

        # Check subscription status for reactivation case
        subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
        is_cancelled_at_period_end = subscription and subscription.cancel_at_period_end

        # Add activate button for inactive establishments
        if not etablissement.active:
            activate_button = {
                "text": "Activer",
                "icon": "fa-solid fa-toggle-on",
                "classes": "btn-sm btn-success w-100",
                "extra_kwargs": {
                    "hx_modal_toggle": True,
                    "hx-get": reverse("dashboard:etablissements:toggle_status_partial", args=[etablissement.id]),
                },
            }
            buttons.append(activate_button)
        elif is_cancelled_at_period_end:
            # Add reactivate button for establishments with cancelled subscription
            reactivate_button = {
                "text": "Réactiver",
                "icon": "fa-solid fa-toggle-on",
                "classes": "btn-sm btn-success w-100",
                "extra_kwargs": {
                    "hx_modal_toggle": True,
                    "hx-get": reverse("dashboard:etablissements:toggle_status_partial", args=[etablissement.id]),
                },
            }
            buttons.append(reactivate_button)
        else:
            # Add deactivate button for active establishments
            deactivate_button = {
                "text": "Désactiver",
                "icon": "fa-solid fa-toggle-off",
                "classes": "btn-sm btn-danger w-100",
                "extra_kwargs": {
                    "hx_modal_toggle": True,
                    "hx-get": reverse("dashboard:etablissements:toggle_status_partial", args=[etablissement.id]),
                },
            }
            buttons.append(deactivate_button)

        # Add delete button
        delete_button = {
            "text": "",
            "icon": "fa-solid fa-trash",
            "classes": "btn-sm btn-danger",
            "extra_kwargs": {},
        }

        # Disable delete button if etablissement is active
        if etablissement.active:
            delete_button["extra_kwargs"]["disabled"] = True
            delete_button["extra_kwargs"]["data-bs-toggle"] = "tooltip"
            delete_button["extra_kwargs"]["data-bs-placement"] = "top"
            delete_button["extra_kwargs"]["title"] = "Vous devez d'abord désactiver l'établissement avant de le supprimer"
        else:
            delete_button["extra_kwargs"]["hx_modal_toggle"] = True
            delete_button["extra_kwargs"]["hx-get"] = reverse("dashboard:etablissements:delete_partial", args=[etablissement.id])

        buttons.append(delete_button)

        # Subscription status logic (reuse subscription from above if available)
        if not subscription:
            subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
        if not subscription:
            subscription_badge = {
                "type": "badge",
                "value": "Aucun abonnement",
                "variant": "secondary",
                "icon": "fa-solid fa-circle",
            }
        elif subscription.cancel_at_period_end:
            subscription_badge = {
                "type": "badge",
                "value": "Actif (annulation)",
                "variant": "success",
                "icon": "fa-solid fa-clock",
                "tooltip": "L'abonnement sera annulé à la fin de la période en cours",
            }
        else:
            subscription_badge = {
                "type": "badge",
                "value": "Actif",
                "variant": "success",
                "icon": "fa-solid fa-check-circle",
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

        row = {
            "title": etablissement.title,
            "created_at": created_at_cell,
            "subscription": subscription_badge,
            "actions": {
                "type": "buttons",
                "buttons": buttons,
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
                    google_credential.create_etablissement_from_location(account_id=location["account_id"], location_id=location_name)

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
    else:
        messages.error(request, "Établissement non trouvé.")
        return redirect("dashboard:etablissements:list")


@google_gmb_connected_required
def unselect_etablissement(request):
    """
    Unselects the currently selected établissement by clearing the session variable.
    """
    if "selected_etablissement" in request.session:
        del request.session["selected_etablissement"]
        messages.success(request, "Établissement désélectionné.")

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
    is_activation = not etablissement.active

    # Check if this is a reactivation case (active etablissement with cancelled subscription)
    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    is_reactivation = etablissement.active and subscription and subscription.cancel_at_period_end

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
        yearly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("yearly")

        monthly_price_data = None
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

        context["monthly_price"] = monthly_price_data
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
    is_activation = not etablissement.active

    # Check if this is a reactivation case (active etablissement with cancelled subscription)
    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    is_reactivation = etablissement.active and subscription and subscription.cancel_at_period_end

    hx_triggers = {
        "close-modal": True,
    }

    # Reactivation
    if is_reactivation:
        try:
            reactivated_subscription = reactivate_subscription_for_etablissement(request.user, etablissement.id)
            if reactivated_subscription:
                # Sync Stripe data to update local database with reactivation status
                sync_stripe_data(request.user)
                messages.success(request, f"L'abonnement de l'établissement {etablissement.title} a été réactivé avec succès.")
                hx_triggers["etablissements-updated"] = True
            else:
                messages.error(request, f"Impossible de réactiver l'abonnement de l'établissement {etablissement.title}.")
        except Exception as e:
            logger.error(f"Error reactivating subscription for etablissement {etablissement.id}: {e}")
            messages.error(
                request,
                f"Une erreur est survenue lors de la réactivation de l'abonnement de l'établissement {etablissement.title}. Veuillez réessayer ou contacter le support.",
            )

    # Activation
    elif is_activation:
        has_active_subscription = etablissement.has_active_subscription()

        # si l'établissement a un abonnement actif, on sync les données de Stripe
        if has_active_subscription:
            sync_stripe_data(request.user)
            hx_triggers["etablissements-updated"] = True

        # si l'établissement n'a pas d'abonnement actif, on redirige vers la sélection du plan d'abonnement
        else:
            # Validate form for price_id when activating without subscription
            form = ToggleEtablissementStatusForm(request.POST)

            if form.is_valid():
                price_id = form.cleaned_data["price_id"]

                request.session["price_id"] = price_id
                request.session["etablissement_id"] = etablissement.id
                return redirect("payments:create_checkout_session")
            else:
                print(form.errors)
                messages.error(request, "Une erreur est survenue lors de la sélection du plan d'abonnement.")

    # Désactivation
    else:
        # Check if etablissement has an active subscription and cancel it
        if etablissement.has_active_subscription():
            try:
                cancelled_subscription = cancel_subscription_for_etablissement(request.user, etablissement.id)
                if cancelled_subscription:
                    # Sync Stripe data to update local database with cancellation status
                    sync_stripe_data(request.user)
                    messages.success(request, f"L'établissement {etablissement.title} a été désactivé. Votre abonnement continuera jusqu'à la fin de la période en cours.")
                else:
                    # Subscription not found or already cancelled, proceed with deactivation
                    messages.success(request, f"L'établissement {etablissement.title} a été désactivé.")
            except Exception as e:
                logger.error(f"Error cancelling subscription for etablissement {etablissement.id}: {e}")
                # Still proceed with deactivation even if cancellation fails
                messages.warning(
                    request,
                    f"L'établissement {etablissement.title} a été désactivé, "
                    "mais une erreur est survenue lors de l'annulation de l'abonnement. "
                    "Veuillez vérifier votre portail de facturation.",
                )
        else:
            messages.success(request, f"L'établissement {etablissement.title} a été désactivé.")

        etablissement.active = False
        etablissement.save()
        hx_triggers["etablissements-updated"] = True

    return redirect("dashboard:etablissements:list")
