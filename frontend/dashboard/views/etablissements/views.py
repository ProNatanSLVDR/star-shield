from allauth.account.decorators import reverse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from auths.models import Etablissement
from starshield.decorators import google_gmb_connected_required
from frontend.dashboard.render import starshield_render
from django.contrib import messages
from .forms import ImportEtablissementForm
import logging
import stripe
from django.conf import settings
from payments.services import get_price_id_from_product, read_pricing_tier

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
        {"label": "Site web", "key": "website_uri", "orderable": False, "icon": "fa-solid fa-globe"},
        {
            "label": "Statut",
            "key": "status",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-circle-check",
        },
        {
            "label": "Date de création",
            "key": "created_at",
            "orderable": True,
            "centered": True,
            "icon": "fa-solid fa-calendar",
        },
        {"label": "Actions", "key": "actions", "centered": True, "icon": "fa-solid fa-gear"},
    ]

    # Prepare table rows
    rows = []
    for etablissement in etablissements:
        buttons = []

        # Add activate button for inactive establishments
        if not etablissement.active:
            activate_button = {
                "text": "Activer",
                "icon": "fa-solid fa-power-off",
                "classes": "btn-sm btn-success",
                "extra_kwargs": {
                    "hx_modal_toggle": True,
                    "hx-get": reverse("dashboard:etablissements:toggle_status_partial", args=[etablissement.id]),
                },
            }
            buttons.append(activate_button)
        else:
            # Add deactivate button for active establishments
            deactivate_button = {
                "text": "Désactiver",
                "icon": "fa-solid fa-power-off",
                "classes": "btn-sm btn-warning",
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

        status_badge = {
            "type": "badge",
            "value": "Actif" if etablissement.active else "Inactif",
            "variant": "success" if etablissement.active else "warning",
        }

        row = {
            "title": etablissement.title,
            "website_uri": etablissement.website_uri or "N/A",
            "status": status_badge,
            "created_at": etablissement.created_at.strftime("%d/%m/%Y") if etablissement.created_at else "N/A",
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
        print(available_locations)
        request.session["available_locations"] = available_locations
        form = ImportEtablissementForm(available_locations=available_locations)

    # Count imported établissements
    imported_count = sum(1 for location in available_locations if location.get("exists", False))

    context = {
        "form": form,
        "available_locations": available_locations,
        "imported_count": imported_count,
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
            "icon": "fa-solid fa-check",
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
    Show toggle status modal (activate/deactivate) with billing explanation.
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)
    is_activation = not etablissement.active

    # Check if user has an active subscription
    subscription = getattr(request.user, "stripe_subscription", None)
    has_active_subscription = subscription is not None and subscription.status == "active"

    # Count active establishments
    active_count = request.user.google_credential.etablissements.filter(active=True).count()
    new_active_count = active_count + 1 if is_activation else active_count - 1

    # Fetch price information from Stripe

    price_id = None
    if has_active_subscription and subscription.price_id:
        price_id = subscription.price_id
    elif is_activation:
        # Default price for new activation if no subscription
        price_id = get_price_id_from_product(settings.STRIPE_PRODUCTS.get("basic_subscription"))

    current_price_amount = 0
    new_price_amount = 0
    price_currency = "EUR"

    if price_id:
        try:
            price = stripe.Price.retrieve(price_id, expand=["tiers"])
            tiers_data = price.tiers
            price_currency = (price.currency or "eur").upper()
            current_price_amount = read_pricing_tier(tiers_data, active_count) / 100
            new_price_amount = read_pricing_tier(tiers_data, new_active_count) / 100
        except Exception as e:
            logger.error(f"Error fetching price from Stripe: {e}")

    context = {
        "etablissement": etablissement,
        "is_activation": is_activation,
        "has_active_subscription": has_active_subscription,
        "active_count": active_count,
        "new_active_count": new_active_count,
        "current_price_amount": current_price_amount,
        "new_price_amount": new_price_amount,
        "price_currency": price_currency,
        "toggle_url": reverse("dashboard:etablissements:toggle_status", args=[etablissement.id]),
        "checkout_url": reverse("payments:create_checkout_session"),
    }

    return starshield_render(
        request,
        "etablissements/toggle_status_partial.html",
        context=context,
    )


@google_gmb_connected_required
@require_POST
def toggle_etablissement_status(request, id):
    """
    Toggle establishment status (activate/deactivate).
    Updates subscription quantity and establishment status.
    """
    etablissement = get_object_or_404(Etablissement, id=id, google_credential=request.user.google_credential)
    is_activation = not etablissement.active

    hx_triggers = {
        "close-modal": True,
    }

    # Validation for activation
    if is_activation:
        # For activation, require active subscription
        subscription = getattr(request.user, "stripe_subscription", None)
        if not subscription or subscription.status != "active":
            messages.error(request, "Vous devez avoir un abonnement actif pour activer un établissement.")
            return starshield_render(
                request,
                "etablissements/toggle_status_partial.html",
                context={
                    "etablissement": etablissement,
                    "is_activation": True,
                    "has_active_subscription": False,
                },
                hx_triggers=hx_triggers,
            )

    try:
        from payments.services import change_subscription_quantity, sync_stripe_data, validate_quantity_sync, get_active_etablissements_count

        validate_quantity_sync(request.user)
        current_active_count = get_active_etablissements_count(request.user)

        new_quantity = current_active_count + 1 if is_activation else max(0, current_active_count - 1)

        # Update subscription quantity
        subscription = getattr(request.user, "stripe_subscription", None)
        if subscription and subscription.status == "active":
            change_subscription_quantity(request.user, quantity=new_quantity)
            sync_stripe_data(request.user)

        # Update establishment status
        etablissement.active = is_activation
        etablissement.save()

        validate_quantity_sync(request.user)

        action_text = "activé" if is_activation else "désactivé"
        messages.success(request, f"L'établissement {etablissement.title} a été {action_text} avec succès.")

        hx_triggers["etablissements-updated"] = True

        return starshield_render(
            request,
            "etablissements/toggle_status_partial.html",
            context={"etablissement": etablissement, "is_activation": is_activation},
            hx_triggers=hx_triggers,
        )

    except Exception as e:
        action_text = "l'activation" if is_activation else "la désactivation"
        logger.error(f"Error during {action_text} of establishment {id}: {e}")
        messages.error(request, f"Une erreur est survenue lors de {action_text} de l'établissement.")
        return starshield_render(
            request,
            "etablissements/toggle_status_partial.html",
            context={"etablissement": etablissement, "is_activation": is_activation},
            hx_triggers=hx_triggers,
        )
