from django.contrib.auth.decorators import login_required
from frontend.dashboard.render import starshield_render
import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def facturation_view(request):
    """
    Display billing/facturation page with subscription information.
    No Stripe sync - only reads from existing database records.
    """
    user = request.user

    # Get subscription from database (no sync)
    subscription = getattr(user, "stripe_subscription", None)

    # Get active établissements count
    active_etablissements_count = 0
    if hasattr(user, "google_credential"):
        active_etablissements_count = user.google_credential.etablissements.filter(active=True).count()

    # Get price information from Stripe if price_id exists
    price_amount = None
    price_currency = None
    if subscription and subscription.price_id:
        try:
            price = stripe.Price.retrieve(subscription.price_id)
            price_amount = price.unit_amount / 100  # Convert from cents to currency unit
            price_currency = price.currency.upper()
        except Exception as e:
            logger.error(f"Error fetching price from Stripe for price_id {subscription.price_id}: {e}")

    context = {
        "subscription": subscription,
        "active_etablissements_count": active_etablissements_count,
        "price_amount": price_amount,
        "price_currency": price_currency,
    }

    return starshield_render(
        request,
        "facturation/index.html",
        context=context,
        page_name="facturation",
    )
