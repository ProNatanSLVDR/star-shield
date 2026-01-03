from allauth.account.decorators import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from auths.models import GoogleCredentials, Etablissement
from starshield.decorators import google_gmb_connected_required
from frontend.dashboard.render import starshield_render
from django.contrib import messages
from .forms import ImportEtablissementForm
import logging

logger = logging.getLogger(__name__)


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
                    "hx-get": reverse("dashboard:etablissements:activate_partial", args=[etablissement.id]),
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
                    "hx-get": reverse("dashboard:etablissements:deactivate_partial", args=[etablissement.id]),
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


@google_gmb_connected_required
def etablissement_selector_partial(request):
    """
    Returns the établissement selector partial for the sidebar.
    Only loaded on demand via HTMX.
    """
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
def activate_etablissement_partial(request, id):
    """
    Show activation modal with billing explanation.
    """
    etablissement = get_object_or_404(
        Etablissement,
        id=id,
        google_credential=request.user.google_credential
    )

    # Check if user has an active subscription
    subscription = getattr(request.user, "stripe_subscription", None)
    has_active_subscription = (
        subscription is not None and
        subscription.status == "active"
    )

    # Count active establishments
    active_count = request.user.google_credential.etablissements.filter(active=True).count()

    context = {
        "etablissement": etablissement,
        "has_active_subscription": has_active_subscription,
        "active_count": active_count,
        "activate_url": reverse("dashboard:etablissements:activate", args=[etablissement.id]),
        "checkout_url": reverse("payments:create_checkout_session"),
    }

    return starshield_render(
        request,
        "etablissements/activate_partial.html",
        context=context,
    )


@google_gmb_connected_required
@require_POST
def activate_etablissement(request, id):
    """
    Activate an establishment.
    If user has subscription: increment quantity and activate.
    If no subscription: should not reach here (handled by checkout flow).
    """
    etablissement = get_object_or_404(
        Etablissement,
        id=id,
        google_credential=request.user.google_credential
    )

    # Check if already active
    if etablissement.active:
        messages.info(request, f"L'établissement {etablissement.title} est déjà actif.")
        hx_triggers = {
            "etablissements-updated": True,
            "close-modal": True,
        }
        return starshield_render(
            request,
            "etablissements/activate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )

    # Check if user has active subscription
    subscription = getattr(request.user, "stripe_subscription", None)
    if not subscription or subscription.status != "active":
        messages.error(request, "Vous devez avoir un abonnement actif pour activer un établissement.")
        hx_triggers = {
            "close-modal": True,
        }
        return starshield_render(
            request,
            "etablissements/activate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )

    try:
        # Import here to avoid circular imports
        from payments.services import increment_subscription_quantity, sync_stripe_data

        # Increment subscription quantity
        increment_subscription_quantity(request.user)

        # Sync subscription data
        sync_stripe_data(request.user)

        # Activate the establishment
        etablissement.active = True
        etablissement.save()

        messages.success(
            request,
            f"L'établissement {etablissement.title} a été activé avec succès."
        )

        hx_triggers = {
            "etablissements-updated": True,
            "close-modal": True,
        }

        return starshield_render(
            request,
            "etablissements/activate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )

    except Exception as e:
        logger.error(f"Error activating establishment {id}: {e}")
        messages.error(request, "Une erreur est survenue lors de l'activation de l'établissement.")
        hx_triggers = {
            "close-modal": True,
        }
        return starshield_render(
            request,
            "etablissements/activate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )


@google_gmb_connected_required
def deactivate_etablissement_partial(request, id):
    """
    Show deactivation modal with billing explanation.
    """
    etablissement = get_object_or_404(
        Etablissement,
        id=id,
        google_credential=request.user.google_credential
    )

    # Check if user has an active subscription
    subscription = getattr(request.user, "stripe_subscription", None)
    has_active_subscription = (
        subscription is not None and
        subscription.status == "active"
    )

    # Count active establishments
    active_count = request.user.google_credential.etablissements.filter(active=True).count()

    context = {
        "etablissement": etablissement,
        "has_active_subscription": has_active_subscription,
        "active_count": active_count,
        "deactivate_url": reverse("dashboard:etablissements:deactivate", args=[etablissement.id]),
    }

    return starshield_render(
        request,
        "etablissements/deactivate_partial.html",
        context=context,
    )


@google_gmb_connected_required
@require_POST
def deactivate_etablissement(request, id):
    """
    Deactivate an establishment.
    Decrements subscription quantity and deactivates the establishment.
    """
    etablissement = get_object_or_404(
        Etablissement,
        id=id,
        google_credential=request.user.google_credential
    )

    # Check if already inactive
    if not etablissement.active:
        messages.info(request, f"L'établissement {etablissement.title} est déjà inactif.")
        hx_triggers = {
            "etablissements-updated": True,
            "close-modal": True,
        }
        return starshield_render(
            request,
            "etablissements/deactivate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )

    try:
        # Import here to avoid circular imports
        from payments.services import decrement_subscription_quantity, sync_stripe_data

        # Decrement subscription quantity if user has active subscription
        subscription = getattr(request.user, "stripe_subscription", None)
        if subscription and subscription.status == "active":
            decrement_subscription_quantity(request.user)
            sync_stripe_data(request.user)

        # Deactivate the establishment
        etablissement.active = False
        etablissement.save()

        messages.success(
            request,
            f"L'établissement {etablissement.title} a été désactivé avec succès."
        )

        hx_triggers = {
            "etablissements-updated": True,
            "close-modal": True,
        }

        return starshield_render(
            request,
            "etablissements/deactivate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )

    except Exception as e:
        logger.error(f"Error deactivating establishment {id}: {e}")
        messages.error(request, "Une erreur est survenue lors de la désactivation de l'établissement.")
        hx_triggers = {
            "close-modal": True,
        }
        return starshield_render(
            request,
            "etablissements/deactivate_partial.html",
            context={"etablissement": etablissement},
            hx_triggers=hx_triggers,
        )
