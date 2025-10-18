from allauth.account.decorators import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from auths.models import GoogleCredentials, Etablissement
from starshield.decorators import google_gmb_connected_required
from apps.dashboard.render import starshield_render
from django.contrib import messages



@google_gmb_connected_required
def list_etablissements_view(request: HttpRequest) -> HttpResponse:
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
        delete_url = reverse('dashboard:etablissements:delete', args=[etablissement.id])
        delete_button = {
            "text": "",
            "icon": "fa-solid fa-trash",
            "classes": "btn-sm btn-danger",
            "extra_kwargs": {
                "default_hx_modal": True,
                "hx-get": delete_url,
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
def import_etablissement_partial_view(request: HttpRequest) -> HttpResponse:

    context = {}
    hx_triggers = {}

    if request.method == "GET":
        available_locations = request.user.google_credential.list_available_locations()
        request.session["available_locations"] = available_locations
        context["available_locations"] = available_locations

    if request.method == "POST":
        hx_triggers["etablissements-updated"] = True
        hx_triggers["close-modal"] = True
        print(request.POST)

    return starshield_render(request, "etablissements/add_partial.html", context=context, hx_triggers=hx_triggers)

@google_gmb_connected_required
@require_http_methods(["GET", "POST"])
def delete_etablissement_partial_view(request: HttpRequest, id: int) -> HttpResponse:
    """
    Pour supprimer un etablissement
    Double confirmation la suppression (modal + hx-confirm)
    """
    hx_triggers = {
        "etablissements-updated": True,
        "close-modal": True
    }
    # on essaye de récupérer l'établissement
    etablissement = Etablissement.objects.filter(id=id, google_credential=request.user.google_credential).first()
    if not etablissement:
        messages.error(request, "Établissement non trouvé.")
        return starshield_render(request, "etablissements/delete_confirmation.html", hx_triggers=hx_triggers)
    
    if request.method == "POST":
        etablissement_title = etablissement.title
        etablissement.delete()
        messages.success(request, f"L'établissement {etablissement_title} a été supprimé.")
        return starshield_render(request, "etablissements/delete_confirmation.html", hx_triggers=hx_triggers)


    return starshield_render(request, "etablissements/delete_confirmation.html", page_name="etablissements")