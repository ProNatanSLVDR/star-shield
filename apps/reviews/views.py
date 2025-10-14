from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from google_auth_oauthlib.flow import Flow
import logging
from urllib.parse import urljoin

from .models import GoogleCredentials


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



def google_auth_start(request: HttpRequest) -> HttpResponse:
    redirect_uri = f"http://{settings.WEBSITE_URL}{reverse("reviews:google_auth_callback")}"

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


def google_auth_callback(request: HttpRequest) -> HttpResponse:
    redirect_uri = f"http://{settings.WEBSITE_URL}{reverse("reviews:google_auth_callback")}"
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

    GoogleCredentials.objects.update_or_create(
        user=request.user,
        defaults={
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": " ".join(credentials.scopes),
        },
    )

    request.session.pop("state", None)

    return redirect(reverse("dashboard:accueil"))