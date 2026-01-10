from django.conf import settings
import logging
import requests
import warnings

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from google_auth_oauthlib.flow import Flow
from django.contrib import messages

from .models import GoogleCredentials


logger = logging.getLogger(__name__)


def get_google_auth_client_config() -> dict[str, dict[str, str]]:
    return {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "project_id": "starshield-app",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        }
    }


def google_gmb_start(request: HttpRequest) -> HttpResponse:
    redirect_uri = f"{settings.WEBSITE_URL}{reverse('auths:google_gmb_callback')}"

    flow = Flow.from_client_config(
        get_google_auth_client_config(),
        scopes=settings.GOOGLE_OAUTH_GMB_SCOPES,
        redirect_uri=redirect_uri,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    request.session["state"] = state

    return redirect(authorization_url)


def google_gmb_callback(request: HttpRequest) -> HttpResponse:
    redirect_uri = f"{settings.WEBSITE_URL}{reverse('auths:google_gmb_callback')}"
    state = request.session.get("state")

    if not state:
        logger.warning("Google OAuth callback without state in session.")
        return HttpResponseBadRequest("Invalid OAuth session state.")

    flow = Flow.from_client_config(
        get_google_auth_client_config(),
        scopes=settings.GOOGLE_OAUTH_GMB_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as e:  # pragma: no cover - defensive catch for OAuth errors
        logger.error(f"Google OAuth token exchange failed: {e}")
        return HttpResponseBadRequest("Unable to complete Google authorization.")

    credentials = flow.credentials

    # Fetch Google account email using OAuth2 userinfo API
    google_account_email = None
    try:
        # Make direct HTTP request to userinfo endpoint
        response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=10,
        )
        if response.status_code == 200:
            user_info = response.json()
            google_account_email = user_info.get("email")
        else:
            logger.warning(f"Failed to fetch Google account email: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to fetch Google account email: {e}")

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
            "has_invalid_grants": False,
            "google_account_email": google_account_email,
        },
    )

    request.session.pop("state", None)

    if google_credential.google_account_email != google_account_email:
        messages.info(request, _("Compte Google My Business reconnecté avec succès (compte différent)."))

    # If user is in onboarding, redirect to import step
    if not request.user.onboarding_completed:
        return redirect(reverse("dashboard:onboarding:import_etablissements"))

    # Otherwise redirect to dashboard
    if google_credential:
        if google_credential.etablissements.all().count() == 0:
            return redirect(reverse("dashboard:accueil"))
    return redirect(reverse("dashboard:accueil"))
