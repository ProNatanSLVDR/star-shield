import json
from unittest.mock import patch

import stripe
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from tests.factories import UserFactory


@override_settings(STRIPE_SECRET_KEY="sk_test_fake", STRIPE_WEBHOOK_SECRET="whsec_test")
class TestStripeWebhook(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("payments:stripe_webhook")

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url,
            data=b"not-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("apps.private.payments.webhooks.stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, mock_construct):
        mock_construct.side_effect = stripe.SignatureVerificationError("bad sig", "sig_header")

        response = self.client.post(
            self.url,
            data=json.dumps({"id": "evt_1", "type": "test"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )

        self.assertEqual(response.status_code, 400)

    @patch("apps.private.payments.webhooks.cache")
    @patch("apps.private.payments.webhooks.stripe.Webhook.construct_event")
    def test_valid_event_returns_200(self, mock_construct, mock_cache):
        mock_cache.get.return_value = None
        mock_construct.return_value = {
            "id": "evt_1",
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_nonexistent"}},
        }

        response = self.client.post(
            self.url,
            data=json.dumps({"id": "evt_1"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid_sig",
        )

        self.assertEqual(response.status_code, 200)
        mock_cache.set.assert_called_once()

    @patch("apps.private.payments.webhooks.cache")
    @patch("apps.private.payments.webhooks.stripe.Webhook.construct_event")
    def test_already_processed_event_is_skipped(self, mock_construct, mock_cache):
        mock_cache.get.return_value = True  # already processed
        mock_construct.return_value = {
            "id": "evt_duplicate",
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_123"}},
        }

        response = self.client.post(
            self.url,
            data=json.dumps({"id": "evt_duplicate"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid_sig",
        )

        self.assertEqual(response.status_code, 200)

    @patch("apps.private.payments.webhooks.sync_stripe_data")
    @patch("apps.private.payments.webhooks.cache")
    @patch("apps.private.payments.webhooks.stripe.Webhook.construct_event")
    def test_syncs_data_for_subscription_event(self, mock_construct, mock_cache, mock_sync):
        user = UserFactory(stripe_customer_id="cus_real")
        mock_cache.get.return_value = None
        mock_construct.return_value = {
            "id": "evt_sub",
            "type": "customer.subscription.updated",
            "data": {"object": {"customer": "cus_real"}},
        }

        response = self.client.post(
            self.url,
            data=json.dumps({"id": "evt_sub"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid_sig",
        )

        self.assertEqual(response.status_code, 200)
        mock_sync.assert_called_once_with(user)
