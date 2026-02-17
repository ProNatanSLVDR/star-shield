import stripe
from django.conf import settings

from starshield.logger import logger

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_price_id_map():
    """Return the basic_subscription price ID mapping from settings."""
    return settings.STRIPE_PRODUCTS.get("basic_subscription", {})


def get_plan_label(price_id):
    """Map a Stripe price_id to its human-readable French label."""
    if not price_id:
        return ""
    price_map = get_price_id_map()
    if price_id == price_map.get("monthly"):
        return "Mensuel"
    if price_id == price_map.get("trimestrial"):
        return "Trimestriel"
    if price_id == price_map.get("yearly"):
        return "Annuel"
    return ""


def get_subscription_state(etablissement):
    """
    Determine the subscription state for an etablissement.

    Returns a dict with:
        - subscription: the StripeSubscription object or None
        - state: "active", "cancellation_pending", or "inactive"
    """
    subscription = etablissement.stripe_subscription.filter(status__in=["active", "trialing"]).first()
    if not subscription:
        state = "inactive"
    elif subscription.cancel_at_period_end:
        state = "cancellation_pending"
    elif etablissement.active:
        state = "active"
    else:
        state = "inactive"
    return {"subscription": subscription, "state": state}


def get_stripe_prices():
    """
    Fetch all 3 price tiers from the Stripe API and calculate savings percentages.

    Returns a dict with keys "monthly", "trimestrial", "yearly", each containing:
        - id, amount, currency (or None if fetch fails)
    Trimestrial and yearly entries also get full_price and savings_percent when applicable.
    """
    price_map = get_price_id_map()
    monthly_price_id = price_map.get("monthly")
    trimestrial_price_id = price_map.get("trimestrial")
    yearly_price_id = price_map.get("yearly")

    result = {"monthly": None, "trimestrial": None, "yearly": None}

    for key, pid in [("monthly", monthly_price_id), ("trimestrial", trimestrial_price_id), ("yearly", yearly_price_id)]:
        if not pid:
            continue
        try:
            price = stripe.Price.retrieve(pid)
            result[key] = {
                "id": pid,
                "amount": price.unit_amount / 100 if price.unit_amount else 0,
                "currency": (price.currency or "eur").upper(),
            }
        except Exception as e:
            logger.error(f"Error fetching {key} price from Stripe: {e}")

    # Calculate savings relative to monthly
    if result["monthly"]:
        monthly_amount = result["monthly"]["amount"]

        if result["trimestrial"]:
            full_price = monthly_amount * 3
            if full_price > result["trimestrial"]["amount"]:
                result["trimestrial"]["full_price"] = full_price
                result["trimestrial"]["savings_percent"] = int(
                    (full_price - result["trimestrial"]["amount"]) / full_price * 100
                )

        if result["yearly"]:
            full_price = monthly_amount * 12
            if full_price > result["yearly"]["amount"]:
                result["yearly"]["full_price"] = full_price
                result["yearly"]["savings_percent"] = int(
                    (full_price - result["yearly"]["amount"]) / full_price * 100
                )

    return result
