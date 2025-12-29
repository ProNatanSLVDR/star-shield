from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import get_user_model
import stripe
from .services import sync_stripe_data
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Events we care about
    # The guide lists many, but since we always sync full state, 
    # we just need to know IF we should sync.
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

    if event['type'] in allowed_events:
        data_object = event['data']['object']
        
        # Extract customer ID
        customer_id = data_object.get('customer')
        
        if customer_id:
            User = get_user_model()
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                sync_stripe_data(user)
            except User.DoesNotExist:
                logger.warning(f"Received webhook for unknown customer: {customer_id}")
            except Exception as e:
                logger.error(f"Error syncing data in webhook: {e}")
        else:
             logger.warning(f"Webhook event {event['type']} has no customer ID")

    return HttpResponse(status=200)

