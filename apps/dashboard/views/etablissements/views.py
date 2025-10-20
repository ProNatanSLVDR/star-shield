from allauth.account.decorators import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from auths.models import GoogleCredentials, Etablissement
from starshield.decorators import google_gmb_connected_required
from apps.dashboard.render import starshield_render
from django.contrib import messages
from .forms import ImportEtablissementForm



@google_gmb_connected_required
def list_etablissements_view(request):
    if not request.htmx:
        return starshield_render(request, "etablissements/list.html", page_name="etablissements")

    etablissements = request.user.google_credential.etablissements.all()

    # Prepare table headers
    headers = [
        {'label': 'Titre', 'key': 'title', 'searchable': True, 'orderable': True},
        {'label': 'Website', 'key': 'website_uri', 'orderable': False},
        {'label': 'Créé', 'key': 'created_at', 'orderable': True, 'centered': True},
        {'label': 'Actions', 'key': 'actions', 'centered': True},
    ]

    # Prepare table rows
    rows = []
    for etablissement in etablissements:
        delete_button = {
            "text": "",
            "icon": "fa-solid fa-trash",
            "classes": "btn-sm btn-danger",
            "extra_kwargs": {
                "hx_modal_toggle": True,
                "hx-get": reverse('dashboard:etablissements:delete_partial', args=[etablissement.id]),
            }
        }
        
        row = {
            'title': etablissement.title,
            'website_uri': etablissement.website_uri or 'N/A',
            'created_at': etablissement.created_at.strftime('%d/%m/%Y') if etablissement.created_at else 'N/A',
            'actions': {
                'type': 'buttons',
                'buttons': [delete_button],
                'centered': True,
            }
        }
        rows.append(row)

    # Prepare context with table data
    context = {
        "etablissements_table": {
            "headers": headers,
            "rows": rows,
        }
    }
    return starshield_render(request, "etablissements/list_partial.html", context=context, page_name="etablissements")


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
                        account_id=location["account_id"],
                        location_id=location_name
                    )
            
            messages.success(request, "Établissements importés avec succès!")
            hx_triggers["etablissements-updated"] = True
            hx_triggers["close-modal"] = True
    else:
        available_locations = request.user.google_credential.list_available_locations()
        request.session["available_locations"] = available_locations
        form = ImportEtablissementForm(available_locations=available_locations)
    
    context = {
        "form": form,
        "available_locations": available_locations,
    }
    return starshield_render(request, "etablissements/add_partial.html", context=context, hx_triggers=hx_triggers)

@google_gmb_connected_required
@require_http_methods(["GET", "POST"])
def delete_etablissement_confirmation_partial(request, id):
    """
    Pour supprimer un etablissement
    Double confirmation la suppression (modal + hx-confirm)
    """
    
    # on essaye de récupérer l'établissement
    etablissement = Etablissement.objects.filter(id=id, google_credential=request.user.google_credential).first()

    hx_triggers = {}
    context = {
        "etablissement_title": None,
        "delete_url": None,
    }

    if etablissement:
        context["etablissement_title"] = etablissement.title
        context["delete_url"] = reverse('dashboard:etablissements:delete_partial', args=[etablissement.id])

        if request.method == "POST":
            etablissement.delete()
            messages.success(request, f"L'établissement {etablissement.title} a été supprimé.")
            hx_triggers["etablissements-updated"] = True
            hx_triggers["close-modal"] = True
    else:
        messages.error(request, "Établissement non trouvé.")
        hx_triggers["etablissements-updated"] = True
        hx_triggers["close-modal"] = True

    return starshield_render(request, "etablissements/delete_partial.html", context=context, hx_triggers=hx_triggers)


@google_gmb_connected_required
def select_etablissement(request, id):
    etablissement = Etablissement.objects.filter(id=id, google_credential=request.user.google_credential).first()

    if etablissement:
        request.session["selected_etablissement"] = etablissement.id
        return redirect("dashboard:reviews:list")
    else:
        messages.error(request, "Établissement non trouvé.")
        return redirect("dashboard:etablissements:list")

