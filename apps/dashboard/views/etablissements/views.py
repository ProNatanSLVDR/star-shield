from allauth.account.decorators import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST
from auths.models import GoogleCredentials, Etablissement
from starshield.decorators import google_gmb_connected_required



@google_gmb_connected_required
def list_etablissements_view(request: HttpRequest) -> HttpResponse:

    return render(request, "etablissements/list.html")


@google_gmb_connected_required
def list_etablissements_partial_view(request: HttpRequest) -> HttpResponse:
    etablissements = request.user.google_credential.etablissements.all()

    # Prepare table headers
    headers = [
        {'label': 'Titre', 'key': 'title', 'searchable': True, 'orderable': True},
        {'label': 'Website', 'key': 'website_uri', 'orderable': False},
        {'label': 'Créé', 'key': 'created_at', 'orderable': True, 'centered': True},
    ]

    # Prepare table rows
    rows = []
    for etablissement in etablissements:
        row = {
            'title': etablissement.title,
            'website_uri': etablissement.website_uri or 'N/A',
            'created_at': etablissement.created_at.strftime('%d/%m/%Y') if etablissement.created_at else 'N/A',
        }
        rows.append(row)

    # Prepare context with table data
    context = {
        "etablissements": etablissements,
        "etablissements_table": {
            "headers": headers,
            "rows": rows,
        }
    }
    return render(request, "etablissements/list_partial.html", context)

@google_gmb_connected_required
def import_etablissement_partial_view(request: HttpRequest) -> HttpResponse:
    available_locations = request.user.google_credential.list_available_locations()

    request.session["available_locations"] = available_locations

    context = {
        "available_locations": available_locations,
    }
    return render(request, "etablissements/add.html")