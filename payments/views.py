from django.shortcuts import redirect, render
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
    Expects 'price_id' in POST data.
    """
    price_id = request.POST.get("price_id")
    if not price_id:
        return HttpResponseBadRequest("Missing price_id")

    try:
        # 1. Ensure customer exists
        customer_id = get_or_create_stripe_customer(request.user)

        # Construct absolute URLs
        base_url = settings.WEBSITE_URL
        if not base_url.startswith("http"):
             # Simple heuristic: localhost -> http, else https
            protocol = "http" if "localhost" in base_url or "127.0.0.1" in base_url else "https"
            base_url = f"{protocol}://{base_url}"

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
            success_url=f"{base_url}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/payments/cancel", 
            metadata={
                "userId": request.user.id,
            },
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
    Syncs Stripe data and redirects to dashboard.
    """
    # 1. Sync data immediately to avoid race conditions
    sync_stripe_data(request.user)
    
    # 2. Redirect to dashboard
    return redirect(settings.LOGIN_REDIRECT_URL)

@login_required
@require_GET
def checkout_cancel(request):
    """
    Handler for cancelled checkout.
    """
    # TODO: Show a nice message or redirect to pricing page
    return redirect("dashboard:accueil")
