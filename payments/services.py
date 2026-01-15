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

    STRIPE_ACTIVE_STATUS = ["active", "trialing"]
    STRIPE_INACTIVE_STATUS = ["incomplete", "incomplete_expired", "past_due"]
    STRIPE_CANCELED_STATUS = ["canceled", "unpaid", "paused"]

    # on garde une liste des etablissements traités pour desactiver les etablissements qui n'ont pas d'abonnement actif
    processed_etablissements_ids = []

    # listes de filtrage et de traitement
    subscriptions_to_filter = []
    subscriptions_to_process = []

    # on check si l'utilisateur a un stripe_customer_id
    if not user.stripe_customer_id:
        logger.warning(f"Cannot sync Stripe data: User {user.id} has no stripe_customer_id")
        return

    # on fetch les abonnements de l'utilisateur
    try:
        all_subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, limit=100, status="all", expand=["data.items.data.price"])
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {user.id}: {e}")
        return

    # on filtre les abonnements pour ne garder que les abonnements qui contiennent l'etablissement_id dans le metadata
    logger.info(f"Found {len(all_subscriptions.data)} subscriptions for user {user.email} ({user.id})")
    for subscription in all_subscriptions.data:
        logger.info(f"Subscription {subscription['id']} - Status: {subscription['status']}")
        if subscription.get("metadata", {}).get("etablissement_id"):
            subscriptions_to_filter.append(subscription)
        else:
            logger.warning(f"Subscription {subscription['id']} has no metadata or etablissement_id")
            # TODO: cancel all subs with no metadata

    # on parcours les abonnements pour garder uniquement l'abonnement le plus récent pour chaque etablissement
    filter_dict = {}
    for subscription in subscriptions_to_filter:
        print("todo")

    # on parcours les abonnements
    for subscription in subscriptions_to_process:
        subscription_id = subscription["id"]

        logger.info(f"Processing subscription {subscription_id}")

        # on check si le metadata existe et contient l'etablissement_id
        metadata = subscription.get("metadata")
        subscription_status = subscription["status"]
        etablissement_id = metadata["etablissement_id"]
        etablissement = Etablissement.objects.filter(google_credential__user=user, id=etablissement_id).first()
        if not etablissement:
            logger.warning(f"Subscription {subscription_id} has no etablissement")
            continue

        logger.info(f"Found etablissement {etablissement.id} for subscription {subscription_id}")
        logger.info(f"Subscription status: {subscription_status}")

        # on ajoute l'etablissement à la liste des etablissements traités
        processed_etablissements_ids.append(etablissement_id)

        # on get le price_id
        price_id = subscription["items"]["data"][0].price.id if subscription["items"]["data"] else None

        # on get le status de cancel_at_period_end
        cancel_at_period_end = False
        if subscription["cancel_at_period_end"] is True:
            cancel_at_period_end = True
        if subscription["cancel_at"] is not None:
            cancel_at_period_end = True

        # Update local database
        if subscription_status not in STRIPE_CANCELED_STATUS:
            sub_obj, created = StripeSubscription.objects.update_or_create(
                etablissement=etablissement,
                subscription_id=subscription_id,
                defaults={
                    "status": subscription_status,
                    "price_id": price_id,
                    "cancel_at_period_end": cancel_at_period_end,
                },
            )
        else:
            StripeSubscription.objects.filter(etablissement=etablissement, subscription_id=subscription_id).delete()

        # Activate etablissement if subscription is active (even if cancelled at period end, keep active until period ends)
        if subscription_status in STRIPE_ACTIVE_STATUS or subscription_status in STRIPE_INACTIVE_STATUS:
            if not etablissement.active:
                etablissement.active = True
                etablissement.save()
                logger.info(f"Activated etablissement {etablissement_id} for active subscription {subscription_id}")
        elif subscription_status in STRIPE_CANCELED_STATUS:
            if etablissement.active:
                etablissement.active = False
                etablissement.save()
                logger.info(f"Deactivated etablissement {etablissement_id} for inactive subscription {subscription_id}")
        else:
            logger.warning(f"Subscription {subscription_id} has unknown status: {subscription_status}")

    # on désactive les etablissements qui n'ont pas d'abonnement actif
    etablissements_to_deactivate = Etablissement.objects.filter(google_credential__user=user, active=True).exclude(id__in=processed_etablissements_ids)
    for etablissement in etablissements_to_deactivate:
        etablissement.active = False
        etablissement.save()
        logger.info(f"Deactivated etablissement {etablissement.id} for inactive subscription")
