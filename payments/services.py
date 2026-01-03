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
            },
        )
        user.stripe_customer_id = customer.id
        user.save(update_fields=["stripe_customer_id"])
        return customer.id
    except Exception as e:
        logger.error(f"Failed to create Stripe customer for user {user.id}: {e}")
        raise


def get_price_id_from_product():
    """
    Fetch the default/active price ID from the Stripe product.
    Returns the first active recurring price ID from the product.
    """
    try:
        product_id = settings.STRIPE_PRODUCTS.get("basic_subscription")
        if not product_id:
            logger.error("STRIPE_PRODUCTS['basic_subscription'] not configured")
            return None

        # Get all prices for this product
        prices = stripe.Price.list(product=product_id, active=True, limit=10)

        # Find the first recurring price (subscription)
        for price in prices.data:
            if price.type == "recurring":
                return price.id

        logger.error(f"No recurring price found for product {product_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to get price ID from product: {e}")
        return None


def change_subscription_quantity(user, quantity=1, increment=False, decrement=False):
    """
    Change the subscription quantity for the user's active subscription.
    If quantity reaches 0, sets cancel_at_period_end to True.
    Returns the updated subscription object.
    """
    if not user.stripe_customer_id:
        logger.warning(f"Cannot change subscription quantity: User {user.id} has no stripe_customer_id")
        return None

    try:
        # Get the user's active subscription
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status="active", limit=1)

        if not subscriptions.data:
            logger.warning(f"No active subscription found for user {user.id}")
            return None

        subscription = dict(subscriptions.data[0])

        # Get the subscription item
        if not subscription["items"]["data"]:
            logger.error(f"Subscription {subscription['id']} has no items")
            return None

        subscription_item = subscription["items"]["data"][0]
        current_quantity = subscription_item.get("quantity") or 1
        if increment:
            new_quantity = current_quantity + 1
        elif decrement:
            new_quantity = max(0, current_quantity - 1)
        else:
            new_quantity = quantity

        # Prepare update parameters
        update_params = {
            "items": [
                {
                    "id": subscription_item["id"],
                    "quantity": new_quantity,
                }
            ],
        }

        # If quantity reaches 0, set cancel_at_period_end to True
        if new_quantity == 0:
            update_params["cancel_at_period_end"] = True

        # Update the subscription quantity
        updated_subscription = stripe.Subscription.modify(
            subscription["id"],
            **update_params,
        )

        logger.info(f"Changed subscription quantity for user {user.id} from {current_quantity} to {new_quantity}")
        if new_quantity == 0:
            logger.info(f"Subscription {subscription['id']} set to cancel at period end")
        return updated_subscription

    except Exception as e:
        logger.error(f"Failed to change subscription quantity for user {user.id}: {e}")
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
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, limit=1, status="all", expand=["data.default_payment_method", "data.items.data.price"])
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {user.id}: {e}")
        return None

    if not subscriptions.data:
        # No subscription found. Update local state to reflect this.
        # We can either delete the record or set status to 'none'.
        # Setting status to 'none' preserves the record existence which might be useful.
        StripeSubscription.objects.filter(user=user).delete()
        return None

    try:
        subscription = dict(subscriptions.data[0])
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {user.id}: {e}")
        return None

    # Extract relevant fields
    price_id = subscription["items"]["data"][0].price.id if subscription["items"]["data"] else None

    # Payment method details
    payment_method_brand = subscription["default_payment_method"]["card"]["brand"]
    payment_method_last4 = subscription["default_payment_method"]["card"]["last4"]

    # Update local database
    sub_obj, created = StripeSubscription.objects.update_or_create(
        user=user,
        defaults={
            "subscription_id": subscription["id"],
            "status": subscription["status"],
            "price_id": price_id,
            "current_period_end": None,
            "current_period_start": None,
            "cancel_at_period_end": subscription["cancel_at_period_end"],
            "payment_method_brand": payment_method_brand,
            "payment_method_last4": payment_method_last4,
        },
    )

    return sub_obj
