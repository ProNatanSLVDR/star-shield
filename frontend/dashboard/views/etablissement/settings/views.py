from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from auths.models import Etablissement
from frontend.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)
from utils.qrcodes import generate_qrcode
from .forms import EtablissementSettingsForm


@google_gmb_connected_required
@selected_etablissement_required
def settings_view(request):
    etablissement = request.etablissement

    context = {
        "etablissement": etablissement,
    }

    return starshield_render(
        request,
        "etablissement/settings/index.html",
        context=context,
        page_name="etablissement_settings",
    )
