from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _


def google_gmb_connected_required(view_func):
    """
    Decorator to ensure the user has a connected Google My Business account.
    If not, redirect to the Google GMB reconnection page.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        has_credential = hasattr(request.user, "google_credential") and request.user.google_credential is not None

        if not has_credential:
            # No credential exists
            return redirect(reverse("dashboard:onboarding:reconnect_google"))

        google_credential = request.user.google_credential

        if not google_credential.is_valid or google_credential.has_invalid_grants:
            # Credential exists but is invalid or has invalid grants
            return redirect(reverse("dashboard:onboarding:reconnect_google"))

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def selected_etablissement_required(view_func):
    """
    Decorator to ensure the user has a selected etablissement.
    If not, redirect to the etablissements list page.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("selected_etablissement"):
            messages.warning(request, _("Veuillez sélectionner un établissement pour accéder à cette page."))
            return redirect(reverse("dashboard:etablissements:list"))
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def unselect_etablissement(view_func):
    """
    Decorator to ensure no établissement is selected.
    If one is selected, redirect to unselect it.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.session.get("selected_etablissement"):
            return redirect(reverse("dashboard:etablissements:unselect"))
        return view_func(request, *args, **kwargs)

    return _wrapped_view
