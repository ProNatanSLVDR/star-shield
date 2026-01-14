import stripe
from django.conf import settings

from auths.models import Etablissement
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


def check_existing_subscription_for_etablissement(user, etablissement_id):
    """
    Check if an etablissement already has a subscription in Stripe.
    Returns the subscription if found, None otherwise.
    """
    if not user.stripe_customer_id:
        return None

    try:
        # Fetch all subscriptions for the customer
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status="all", limit=100)

        # Check if any subscription has this etablissement_id in metadata
        for subscription in subscriptions.data:
            metadata = subscription.get("metadata", {})
            if metadata.get("etablissement_id") == str(etablissement_id):
                return subscription
        return None
    except Exception as e:
        logger.error(f"Failed to check existing subscriptions for etablissement {etablissement_id}: {e}")
        return None


def cancel_subscription_for_etablissement(user, etablissement_id):
    """
    Cancel the subscription for an etablissement in Stripe at period end.
    Returns the cancelled subscription object or None if not found/already cancelled.
    """
    if not user.stripe_customer_id:
        logger.warning(f"Cannot cancel subscription: User {user.id} has no stripe_customer_id")
        return None

    try:
        # Find the subscription for this etablissement
        subscription = check_existing_subscription_for_etablissement(user, etablissement_id)

        if not subscription:
            logger.warning(f"No subscription found for etablissement {etablissement_id}")
            return None

        subscription_id = subscription["id"]
        subscription_status = subscription.get("status")

        # Check if subscription is already cancelled or scheduled for cancellation
        if subscription_status == "canceled":
            logger.info(f"Subscription {subscription_id} is already cancelled")
            return subscription

        if subscription.get("cancel_at_period_end") is True:
            logger.info(f"Subscription {subscription_id} is already scheduled for cancellation at period end")
            return subscription

        # Cancel at period end (not immediately)
        cancelled_subscription = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)

        logger.info(f"Successfully scheduled cancellation for subscription {subscription_id} at period end")
        return cancelled_subscription

    except Exception as e:
        logger.error(f"Failed to cancel subscription for etablissement {etablissement_id}: {e}")
        return None


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
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, limit=100, status="all", expand=["data.items.data.price"])
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {user.id}: {e}")
        return None

    if not subscriptions.data:
        StripeSubscription.objects.filter(etablissement__google_credential__user=user).delete()
        return None
    print(f"syncing stripe data for user {user.id}")
    # we get all etablissements from the user (not just active ones)
    etablissements = Etablissement.objects.filter(google_credential__user=user)
    print(f"etablissements: {etablissements}")

    # Track processed subscription IDs to clean up orphaned records
    processed_subscription_ids = []

    for subscription in subscriptions.data:
        subscription_id = subscription["id"]

        # Validate metadata exists and contains etablissement_id
        metadata = subscription.get("metadata")
        if not metadata or "etablissement_id" not in metadata:
            logger.warning(f"Subscription {subscription_id} has no metadata or etablissement_id")
            continue

        etablissement_id = metadata["etablissement_id"]

        etablissement = Etablissement.objects.filter(google_credential__user=user, id=etablissement_id).first()
        if not etablissement:
            logger.warning(f"Subscription {subscription_id} has no etablissement")
            continue

        # we get the subscription status
        subscription_status = subscription["status"]

        # Track this subscription ID (only for non-canceled subscriptions)
        processed_subscription_ids.append(subscription_id)

        # we exclude the etablissement from the list (to keep only the etablissements without a subscription)
        etablissements = etablissements.exclude(id=etablissement.id)

        # we get the price_id
        price_id = subscription["items"]["data"][0].price.id if subscription["items"]["data"] else None

        # we get the cancel_at_period_end status
        cancel_at_period_end = False
        if subscription["cancel_at_period_end"] is True:
            cancel_at_period_end = True
        if subscription["cancel_at"] is not None:
            cancel_at_period_end = True

        # Update local database
        sub_obj, created = StripeSubscription.objects.update_or_create(
            etablissement=etablissement,
            subscription_id=subscription_id,
            defaults={
                "status": subscription_status,
                "price_id": price_id,
                "cancel_at_period_end": cancel_at_period_end,
            },
        )

        # Activate etablissement if subscription is active (even if cancelled at period end, keep active until period ends)
        if subscription_status == "active":
            etablissement.active = True
            etablissement.save()
            logger.info(f"Activated etablissement {etablissement_id} for active subscription {subscription_id}")
        elif subscription_status == "canceled":
            StripeSubscription.objects.filter(etablissement=etablissement, subscription_id=subscription_id).delete()
            etablissement.active = False
            etablissement.save()
            logger.info(f"Deleted StripeSubscription record for canceled subscription {subscription_id}")
            continue
        else:
            etablissement.active = False
            etablissement.save()
            logger.info(f"Deactivated etablissement {etablissement_id} for inactive subscription {subscription_id}")

    # Delete orphaned local subscriptions that no longer exist in Stripe
    if processed_subscription_ids:
        StripeSubscription.objects.filter(etablissement__google_credential__user=user).exclude(subscription_id__in=processed_subscription_ids).delete()

    # Deactivate etablissements without active subscriptions
    for etablissement in etablissements:
        if etablissement.active:
            etablissement.active = False
            etablissement.save()
            logger.info(f"Deactivated etablissement {etablissement.id} - no active subscription")
