import stripe
from django.conf import settings
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


def get_price_id_from_product(product_id):
    """
    Fetch the default/active price ID from the Stripe product.
    """
    try:
        if not product_id:
            logger.error("No product ID given")
            return None

        prices = stripe.Product.retrieve(product_id)

        price = prices.default_price

        return price
    except Exception as e:
        logger.error(f"Failed to get price ID from product {product_id}: {e}")
        return None


def read_pricing_tier(tiers_data, quantity):
    """
    Read the pricing tier for a given quantity.
    Expects the following structure:

    "tiers": [
        {
            "flat_amount": null,
            "flat_amount_decimal": null,
            "unit_amount": 5000,
            "unit_amount_decimal": "5000",
            "up_to": 3
        },
        {
            "flat_amount": 2000,
            "flat_amount_decimal": "2000",
            "unit_amount": 3000,
            "unit_amount_decimal": "3000",
            "up_to": 10
        },
        {
            "flat_amount": 20000,
            "flat_amount_decimal": "20000",
            "unit_amount": 2000,
            "unit_amount_decimal": "2000",
            "up_to": null
        }
    ],
    """
    # Track where the previous tier ended
    total_amount = 0
    current_tier_index = 0
    tier_first = True

    if quantity <= 0:
        return 0

    for i in range(1, quantity + 1):
        # if its the first time we enter this tier, we add the flat amount
        if tier_first:
            tier_first = False

            flat_amount = tiers_data[current_tier_index]["flat_amount"]
            if flat_amount is not None:
                total_amount += flat_amount

        unit_amount = tiers_data[current_tier_index]["unit_amount"]
        if unit_amount is not None:
            total_amount += unit_amount

        # test if we need to move to the next tier
        if i == tiers_data[current_tier_index].get("up_to"):
            current_tier_index += 1
            tier_first = True

    return total_amount


def get_stripe_subscription_quantity(user):
    """
    Fetch the current subscription quantity from Stripe.
    Returns the quantity or None if no active subscription found.
    """
    if not user.stripe_customer_id:
        return None

    try:
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status="active", limit=1)
        if not subscriptions.data:
            return None

        subscription = subscriptions.data[0]
        if not subscription["items"]["data"]:
            return None

        subscription_item = subscription["items"]["data"][0]
        return subscription_item.get("quantity") or 0
    except Exception as e:
        logger.error(f"Failed to get Stripe subscription quantity for user {user.id}: {e}")
        return None


def get_active_etablissements_count(user):
    """
    Count the number of active établissements for a user.
    Returns 0 if user has no google_credential.
    """
    try:
        if hasattr(user, "google_credential") and user.google_credential:
            return user.google_credential.etablissements.filter(active=True).count()
        return 0
    except Exception as e:
        logger.error(f"Failed to get active établissements count for user {user.id}: {e}")
        return 0


def validate_quantity_sync(user):
    """
    Sync établissements to match Stripe subscription quantity.
    Stripe is the source of truth - establishments are adjusted to match.
    Returns True if sync was successful, False otherwise.
    """
    stripe_quantity = get_stripe_subscription_quantity(user)
    active_count = get_active_etablissements_count(user)

    # Handle case where user has no google_credential
    if not hasattr(user, "google_credential") or not user.google_credential:
        if stripe_quantity is None or stripe_quantity == 0:
            return True
        logger.warning(f"User {user.id}: Has Stripe quantity {stripe_quantity} but no google_credential")
        return False

    try:
        etablissements = user.google_credential.etablissements

        # Case 1: No subscription exists - deactivate all establishments
        if stripe_quantity is None:
            if active_count == 0:
                return True

            # Deactivate all establishments
            deactivated = etablissements.filter(active=True).update(active=False)
            logger.info(f"User {user.id}: No active Stripe subscription - deactivated {deactivated} établissements")
            return True

        # Case 2: Stripe quantity > active establishments - activate needed establishments
        if stripe_quantity > active_count:
            needed = stripe_quantity - active_count
            inactive_queryset = etablissements.filter(active=False).order_by("id")
            available_count = inactive_queryset.count()

            if available_count < needed:
                logger.warning(
                    f"User {user.id}: Stripe quantity is {stripe_quantity} but only "
                    f"{available_count} inactive établissements available. "
                    f"Activating {available_count} establishments."
                )

            inactive_etablissements = inactive_queryset[:needed]
            activated_ids = list(inactive_etablissements.values_list("id", flat=True))
            etablissements.filter(id__in=activated_ids).update(active=True)

            if activated_ids:
                logger.info(f"User {user.id}: Activated {len(activated_ids)} établissements (IDs: {activated_ids}) to match Stripe quantity {stripe_quantity}")
            return True

        # Case 3: Stripe quantity < active establishments - deactivate excess establishments
        if stripe_quantity < active_count:
            excess = active_count - stripe_quantity
            active_etablissements = etablissements.filter(active=True).order_by("id")[:excess]

            deactivated_ids = list(active_etablissements.values_list("id", flat=True))
            etablissements.filter(id__in=deactivated_ids).update(active=False)

            if deactivated_ids:
                logger.info(f"User {user.id}: Deactivated {len(deactivated_ids)} établissements (IDs: {deactivated_ids}) to match Stripe quantity {stripe_quantity}")
            return True

        # Case 4: Already in sync
        return True

    except Exception as e:
        logger.error(f"Failed to sync établissements for user {user.id}: {e}")
        return False


def change_subscription_quantity(user, quantity):
    """
    Set the subscription quantity for the user's active subscription to the specified value.
    If quantity reaches 0, sets cancel_at_period_end to True.
    If reactivating from 0 (going to 1+), removes cancel_at_period_end.
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
        else:
            update_params["cancel_at_period_end"] = False

        # Always invoice immediately when changing quantity
        update_params["proration_behavior"] = "always_invoice"

        # Update the subscription quantity
        updated_subscription = stripe.Subscription.modify(
            subscription["id"],
            **update_params,
        )

        logger.info(f"Changed subscription quantity for user {user.id} from {current_quantity} to {new_quantity}")
        if new_quantity == 0:
            logger.info(f"Subscription {subscription['id']} set to cancel at period end")

        # Validate quantity sync after update
        validate_quantity_sync(user)

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
        subscription = subscriptions.data[0]
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {user.id}: {e}")
        return None

    # Extract relevant fields
    price_id = subscription["items"]["data"][0].price.id if subscription["items"]["data"] else None

    # Payment method details
    payment_method_brand = subscription["default_payment_method"]["card"]["brand"] if subscription["default_payment_method"] else None
    payment_method_last4 = subscription["default_payment_method"]["card"]["last4"] if subscription["default_payment_method"] else None

    cancel_at_period_end = True if subscription["cancel_at_period_end"] is True or subscription["cancel_at"] is not None else False
    print(f"cancel_at_period_end: {subscription['cancel_at_period_end']}")
    print(f"cancel_at: {subscription['cancel_at']}")
    # Update local database
    sub_obj, created = StripeSubscription.objects.update_or_create(
        user=user,
        defaults={
            "subscription_id": subscription["id"],
            "status": subscription["status"],
            "price_id": price_id,
            "current_period_end": None,
            "current_period_start": None,
            "cancel_at_period_end": cancel_at_period_end,
            "payment_method_brand": payment_method_brand,
            "payment_method_last4": payment_method_last4,
        },
    )

    return sub_obj
