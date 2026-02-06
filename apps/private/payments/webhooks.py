import json

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from starshield.logger import logger

from .services import sync_stripe_data

WEBHOOK_EVENT_CACHE_TTL = 60 * 60 * 24  # 24 hours


@csrf_exempt
@require_POST
@login_not_required
def stripe_webhook(request):
    event = None
    payload = request.body
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        logger.error(f"Webhook error while parsing basic request: {e}")
        return HttpResponse(status=400)

    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return HttpResponse(status=400)

    # Idempotency: skip already-processed events
    event_id = event.get("id")
    cache_key = f"stripe_webhook_{event_id}"
    if cache.get(cache_key):
        logger.info(f"Skipping already-processed webhook event {event_id}")
        return HttpResponse(status=200)

    allowed_events = [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
        "customer.subscription.pending_update_applied",
        "customer.subscription.pending_update_expired",
        "customer.subscription.trial_will_end",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.payment_action_required",
        "invoice.upcoming",
        "invoice.marked_uncollectible",
        "invoice.payment_succeeded",
    ]

    if event["type"] in allowed_events:
        data_object = event["data"]["object"]

        # Extract customer ID
        customer_id = data_object.get("customer")

        if customer_id:
            User = get_user_model()
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                sync_stripe_data(user)
                logger.info(f"Synced stripe data for user {user} : {user.id}")
            except User.DoesNotExist:
                logger.error(f"Received webhook for unknown customer: {customer_id}")
            except Exception as e:
                logger.error(f"Error syncing data in webhook: {e}")
                return HttpResponse(status=500)
        else:
            logger.warning(f"Webhook event {event['type']} has no customer ID")

        logger.info(f"Webhook event {event['type']} processed successfully")

    # Mark event as processed
    cache.set(cache_key, True, WEBHOOK_EVENT_CACHE_TTL)
    return HttpResponse(status=200)
