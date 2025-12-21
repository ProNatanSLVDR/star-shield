from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging
from urllib.parse import urljoin

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from google_auth_oauthlib.flow import Flow
from django.contrib import messages

from .models import Etablissement, GoogleCredentials


logger = logging.getLogger(__name__)


def get_google_auth_client_config() -> dict[str, dict[str, str]]:
    return {
        "web": {
            "client_id": settings.GOOGLE_GMB_CLIENT_ID,
            "project_id": "starshield-app",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_GMB_CLIENT_SECRET,
        }
    }


def google_gmb_start(request: HttpRequest) -> HttpResponse:
    protocol = "https" if request.is_secure() else "http"

    redirect_uri = f"{protocol}://{settings.WEBSITE_URL}{reverse('auths:google_gmb_callback')}"

    flow = Flow.from_client_config(
        get_google_auth_client_config(),
        scopes=settings.GOOGLE_GMB_SCOPES,
        redirect_uri=redirect_uri,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    request.session["state"] = state

    return redirect(authorization_url)


def google_gmb_callback(request: HttpRequest) -> HttpResponse:
    protocol = "https" if request.is_secure() else "http"

    redirect_uri = f"{protocol}://{settings.WEBSITE_URL}{reverse('auths:google_gmb_callback')}"
    state = request.session.get("state")

    if not state:
        logger.warning("Google OAuth callback without state in session.")
        return HttpResponseBadRequest("Invalid OAuth session state.")

    flow = Flow.from_client_config(
        get_google_auth_client_config(),
        scopes=settings.GOOGLE_GMB_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as exc:  # pragma: no cover - defensive catch for OAuth errors
        logger.exception("Google OAuth token exchange failed: %%s", exc)
        return HttpResponseBadRequest("Unable to complete Google authorization.")

    credentials = flow.credentials

    google_credential, created = GoogleCredentials.objects.update_or_create(
        user=request.user,
        client_id=credentials.client_id,
        defaults={
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_secret": credentials.client_secret,
            "scopes": " ".join(credentials.scopes),
            "is_valid": True,
        },
    )

    request.session.pop("state", None)

    messages.success(request, _("Compte Google My Business connecté avec succès."))

    # If user is in onboarding, redirect to import step
    if not request.user.onboarding_completed:
        return redirect(reverse("dashboard:onboarding:import_etablissements"))

    # Otherwise redirect to dashboard
    if google_credential:
        if google_credential.etablissements.all().count() == 0:
            return redirect(reverse("dashboard:accueil"))
    return redirect(reverse("dashboard:accueil"))
