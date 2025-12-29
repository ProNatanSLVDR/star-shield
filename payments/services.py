import stripe
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from .models import StripeSubscription
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

def get_or_create_stripe_customer(user):
    """
    Ensure the user has a Stripe Customer ID.
    If not, create one in Stripe and save it to the User model.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    try:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={
                "userId": user.id,
            }
        )
        user.stripe_customer_id = customer.id
        user.save(update_fields=["stripe_customer_id"])
        return customer.id
    except Exception as e:
        logger.error(f"Failed to create Stripe customer for user {user.id}: {e}")
        raise

def sync_stripe_data(user):
    """
    Sync subscription data from Stripe to the local database.
    This is the single source of truth for subscription state.
    """
    if not user.stripe_customer_id:
        logger.warning(f"Cannot sync Stripe data: User {user.id} has no stripe_customer_id")
        return None

    try:
        # Fetch latest subscription data from Stripe
        subscriptions = stripe.Subscription.list(
            customer=user.stripe_customer_id,
            limit=1,
            status="all",
            expand=["data.default_payment_method"]
        )
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {user.id}: {e}")
        return None

    if not subscriptions.data:
        # No subscription found. Update local state to reflect this.
        # We can either delete the record or set status to 'none'.
        # Setting status to 'none' preserves the record existence which might be useful.
        StripeSubscription.objects.update_or_create(
            user=user,
            defaults={
                "subscription_id": "",
                "status": "none",
                "price_id": None,
                "current_period_end": None,
                "current_period_start": None,
                "cancel_at_period_end": False,
                "payment_method_brand": None,
                "payment_method_last4": None,
            }
        )
        return None

    subscription = subscriptions.data[0]
    
    # Extract relevant fields
    price_id = subscription.items.data[0].price.id if subscription.items.data else None
    
    # Handle timestamps (Stripe uses unix timestamps)
    current_period_end = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
    current_period_start = datetime.fromtimestamp(subscription.current_period_start, tz=timezone.utc)
    
    # Payment method details
    payment_method_brand = None
    payment_method_last4 = None
    
    if subscription.default_payment_method and isinstance(subscription.default_payment_method, dict):
        pm = subscription.default_payment_method
        if pm.get("card"):
            payment_method_brand = pm["card"].get("brand")
            payment_method_last4 = pm["card"].get("last4")
    elif subscription.default_payment_method and hasattr(subscription.default_payment_method, 'card'):
         # If it's a stripe object
        payment_method_brand = subscription.default_payment_method.card.brand
        payment_method_last4 = subscription.default_payment_method.card.last4


    # Update local database
    sub_obj, created = StripeSubscription.objects.update_or_create(
        user=user,
        defaults={
            "subscription_id": subscription.id,
            "status": subscription.status,
            "price_id": price_id,
            "current_period_end": current_period_end,
            "current_period_start": current_period_start,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "payment_method_brand": payment_method_brand,
            "payment_method_last4": payment_method_last4,
        }
    )
    
    return sub_obj

