from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from auths.models import GoogleCredentials



@login_required
def accueil_view(request: HttpRequest) -> HttpResponse:
    context = {
    }
    return render(request, "accueil.html", context)


@login_required
@require_POST
def refresh_etablissements_view(request: HttpRequest) -> HttpResponse:
    credentials = GoogleCredentials.objects.filter(user=request.user).first()

    if not credentials:
        messages.error(request, _("Aucun compte Google My Business n'est connecté."))
        return redirect(reverse("dashboard:accueil"))

    try:
        sync_result: SyncResult = sync_etablissements(credentials)
    except Exception as exc:  # pragma: no cover - defensive guard
        messages.error(request, _("La synchronisation des établissements a échoué."))
        return redirect(reverse("dashboard:accueil"))

    if sync_result.errors:
        for error in sync_result.errors:
            messages.error(request, error)

    if sync_result.success:
        messages.success(
            request,
            _(
                "Synchronisation terminée : %(created)s créé(s), %(updated)s mis à jour."
            )
            % {"created": sync_result.created, "updated": sync_result.updated},
        )

    return redirect(reverse("dashboard:accueil"))

