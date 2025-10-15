from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _

def google_gmb_connected_required(view_func):
    """
    Decorator to ensure the user has a connected Google My Business account.
    If not, redirect to the Google GMB connection/setup page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if (
            not hasattr(request.user, "google_credential") or
            not request.user.google_credential.is_valid
        ):
            messages.warning(request, _("Veuillez connecter votre compte Google My Business pour accéder à cette page."))
            return redirect(reverse("dashboard:accueil"))
        return view_func(request, *args, **kwargs)
    return _wrapped_view
