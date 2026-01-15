from django.http.response import Http404
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET, require_http_methods
import stripe

from auths.models import Etablissement
from .services import get_or_create_stripe_customer, sync_stripe_data, check_existing_subscription_for_etablissement
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
@require_http_methods(["GET", "POST"])
def create_checkout_session(request):
    """
    Create a Stripe Checkout Session and redirect the user to it.
    Accepts 'price_id' and 'etablissement_id' from POST or GET.
    If price_id not provided, will fetch from product default.
    """
    # Support both GET (for redirects) and POST (for forms)
    price_id = request.session.get("price_id", None)
    etablissement_id = request.session.get("etablissement_id", None)

    etablissement = Etablissement.objects.filter(id=etablissement_id, google_credential__user=request.user).first()

    if not etablissement:
        logger.warning(f"Etablissement not found for id {etablissement_id}")
        raise Http404("Établissement non trouvé")

    if not price_id:
        logger.warning(f"Price ID not found for etablissement {etablissement_id}")
        raise Http404("Le plan d'abonnement n'a pas été trouvé")

    # Check database for existing subscription
    existing_subscription_db = etablissement.stripe_subscription.first()

    # Check Stripe API for existing subscription
    existing_subscription_stripe = check_existing_subscription_for_etablissement(request.user, etablissement_id)

    # If subscription exists in either place, handle it
    if existing_subscription_db or existing_subscription_stripe:
        # Sync to ensure database is up to date
        sync_stripe_data(request.user)

        # Refresh database record if it exists
        if existing_subscription_db:
            existing_subscription_db.refresh_from_db()
            if existing_subscription_db.status == "active":
                logger.warning(f"Etablissement {etablissement_id} already has an active subscription {existing_subscription_db.subscription_id}")
                raise Http404("Cet établissement a déjà un abonnement actif")

        # Also check Stripe subscription status
        if existing_subscription_stripe and existing_subscription_stripe.status == "active":
            logger.warning(f"Etablissement {etablissement_id} already has an active subscription in Stripe {existing_subscription_stripe.id}")
            raise Http404("Cet établissement a déjà un abonnement actif")

    try:
        # 1. Ensure customer exists
        customer_id = get_or_create_stripe_customer(request.user)
    except Exception as e:
        logger.error(f"Error getting or creating stripe customer: {e}")
        raise

    # Build success URL with etablissement_id if provided
    success_url = f"{settings.WEBSITE_URL}/payments/success?session_id={{CHECKOUT_SESSION_ID}}"
    if etablissement_id:
        success_url += f"&etablissement_id={etablissement_id}"

    # Build metadata
    metadata = {
        "userId": request.user.id,
    }
    if etablissement_id:
        metadata["etablissement_id"] = etablissement_id

    try:
        # 2. Create Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=f"{settings.WEBSITE_URL}/payments/cancel",
            subscription_data={
                "metadata": metadata,
            },
            # Optional: Allow promotion codes
            allow_promotion_codes=True,
        )

        # Redirect to Stripe
        return redirect(checkout_session.url)

    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise


@login_required
@require_GET
def checkout_success(request):
    """
    Handler for successful checkout return.
    Syncs Stripe data and activates establishment if etablissement_id is provided.
    """
    etablissement_id = request.GET.get("etablissement_id")

    # 1. Sync data immediately to avoid race conditions
    sync_stripe_data(request.user)

    # 3. Redirect to dashboard (or establishment list if we came from activation)
    if etablissement_id:
        return redirect("dashboard:etablissements:list")
    return redirect(settings.LOGIN_REDIRECT_URL)


@login_required
@require_GET
def checkout_cancel(request):
    """
    Handler for cancelled checkout.
    """
    # TODO: Show a nice message or redirect to pricing page
    return redirect("dashboard:accueil")


@login_required
@require_POST
def stripe_customer_portal(request):
    """
    Create a Stripe Customer Portal Session and redirect the user to it.
    """

    customer_id = get_or_create_stripe_customer(request.user)
    stripe_customer_portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.WEBSITE_URL}/payments/success",
    )
    return redirect(stripe_customer_portal_session.url)
