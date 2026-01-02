from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseBadRequest
import stripe
from .services import get_or_create_stripe_customer, sync_stripe_data
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
@require_POST
def create_checkout_session(request):
    """
    Create a Stripe Checkout Session and redirect the user to it.
    Expects 'price_id' in POST data, or will fetch from product if not provided.
    Optionally accepts 'etablissement_id' to activate establishment after payment.
    """
    price_id = request.POST.get("price_id")
    etablissement_id = request.POST.get("etablissement_id")

    # If no price_id provided, fetch from product
    if not price_id:
        from .services import get_price_id_from_product

        price_id = get_price_id_from_product()
        if not price_id:
            return HttpResponseBadRequest("Could not determine price_id")

    try:
        # 1. Ensure customer exists
        customer_id = get_or_create_stripe_customer(request.user)

        # Construct absolute URLs
        base_url = settings.WEBSITE_URL
        if not base_url.startswith("http"):
            # Simple heuristic: localhost -> http, else https
            protocol = "http" if "localhost" in base_url or "127.0.0.1" in base_url else "https"
            base_url = f"{protocol}://{base_url}"

        # Build success URL with etablissement_id if provided
        success_url = f"{base_url}/payments/success?session_id={{CHECKOUT_SESSION_ID}}"
        if etablissement_id:
            success_url += f"&etablissement_id={etablissement_id}"

        # Build metadata
        metadata = {
            "userId": request.user.id,
        }
        if etablissement_id:
            metadata["etablissement_id"] = etablissement_id

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
            cancel_url=f"{base_url}/payments/cancel",
            metadata=metadata,
            # Optional: Allow promotion codes
            allow_promotion_codes=True,
        )

        # Redirect to Stripe
        return redirect(checkout_session.url)

    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_GET
def checkout_success(request):
    """
    Handler for successful checkout return.
    Syncs Stripe data and activates establishment if etablissement_id is provided.
    """
    session_id = request.GET.get("session_id")
    etablissement_id = request.GET.get("etablissement_id")

    # 1. Sync data immediately to avoid race conditions
    sync_stripe_data(request.user)

    # 2. If etablissement_id is provided, activate the establishment
    if etablissement_id:
        try:
            # Retrieve session to get metadata (as backup)
            if session_id:
                session = stripe.checkout.Session.retrieve(session_id)
                # Use metadata from session if query param not available
                if not etablissement_id and session.metadata.get("etablissement_id"):
                    etablissement_id = session.metadata.get("etablissement_id")

            if etablissement_id:
                from auths.models import Etablissement

                etablissement = Etablissement.objects.filter(id=etablissement_id, google_credential=request.user.google_credential).first()

                if etablissement and not etablissement.active:
                    etablissement.active = True
                    etablissement.save()
                    logger.info(f"Activated establishment {etablissement_id} for user {request.user.id} after checkout")

                    # Redirect to establishment list with success message
                    from django.contrib import messages

                    messages.success(request, f"L'établissement {etablissement.title} a été activé avec succès !")
                    return redirect("dashboard:etablissements:list")

        except Exception as e:
            logger.error(f"Error activating establishment after checkout: {e}")
            # Continue to normal redirect even if activation fails

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
        return_url=f"http://{settings.WEBSITE_URL}/payments/success",
    )
    return redirect(stripe_customer_portal_session.url)
