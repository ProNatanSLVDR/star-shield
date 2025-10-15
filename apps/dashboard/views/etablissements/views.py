from allauth.account.decorators import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST
from auths.models import GoogleCredentials, Etablissement
from starshield.decorators import google_gmb_connected_required



@google_gmb_connected_required
def management_view(request: HttpRequest) -> HttpResponse:

    etablissements = request.user.google_credential.etablissements.all()

    context = {
        "etablissements": etablissements,
    }
    return render(request, "etablissements/list.html", context)


@google_gmb_connected_required
def add_etablissement_view(request: HttpRequest) -> HttpResponse:
    available_locations = request.user.google_credential.list_available_locations()

    request.session["available_locations"] = available_locations

    context = {
        "available_locations": available_locations,
    }
    return render(request, "etablissements/add.html")