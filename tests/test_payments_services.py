from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.private.payments.services import (
    cancel_subscription_for_etablissement,
    change_plan_for_etablissement,
    check_existing_subscription_for_etablissement,
    get_or_create_stripe_customer,
    get_pending_plan_change,
    get_price_id_from_product,
    reactivate_subscription_for_etablissement,
    sync_stripe_data,
)
from tests.factories import EtablissementFactory, UserFactory


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestGetOrCreateStripeCustomer(TestCase):
    def test_returns_existing_customer_id(self):
        user = UserFactory(stripe_customer_id="cus_existing")

        result = get_or_create_stripe_customer(user)

        self.assertEqual(result, "cus_existing")

    @patch("apps.private.payments.services.stripe.Customer.create")
    def test_creates_new_customer(self, mock_create):
        mock_create.return_value = MagicMock(id="cus_new123")
        user = UserFactory(stripe_customer_id=None)

        result = get_or_create_stripe_customer(user)

        self.assertEqual(result, "cus_new123")
        mock_create.assert_called_once()
        user.refresh_from_db()
        self.assertEqual(user.stripe_customer_id, "cus_new123")

    @patch("apps.private.payments.services.stripe.Customer.create")
    def test_api_error_raises(self, mock_create):
        mock_create.side_effect = Exception("Stripe API error")
        user = UserFactory(stripe_customer_id=None)

        with self.assertRaises(Exception):  # noqa: B017
            get_or_create_stripe_customer(user)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestGetPriceIdFromProduct(TestCase):
    @patch("apps.private.payments.services.stripe.Product.retrieve")
    def test_returns_default_price(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(default_price="price_123")

        result = get_price_id_from_product("prod_123")

        self.assertEqual(result, "price_123")

    def test_returns_none_for_empty_product_id(self):
        result = get_price_id_from_product("")

        self.assertIsNone(result)

    @patch("apps.private.payments.services.stripe.Product.retrieve")
    def test_api_error_returns_none(self, mock_retrieve):
        mock_retrieve.side_effect = Exception("Stripe API error")

        result = get_price_id_from_product("prod_123")

        self.assertIsNone(result)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestCheckExistingSubscription(TestCase):
    def test_returns_none_when_no_customer_id(self):
        user = UserFactory(stripe_customer_id=None)

        result = check_existing_subscription_for_etablissement(user, 1)

        self.assertIsNone(result)

    @patch("apps.private.payments.services.stripe.Subscription.list")
    def test_finds_subscription_by_metadata(self, mock_list):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_list.return_value = MagicMock(
            data=[
                {"id": "sub_1", "metadata": {"etablissement_id": "42"}},
                {"id": "sub_2", "metadata": {"etablissement_id": "99"}},
            ]
        )

        result = check_existing_subscription_for_etablissement(user, 42)

        self.assertEqual(result["id"], "sub_1")

    @patch("apps.private.payments.services.stripe.Subscription.list")
    def test_returns_none_when_no_match(self, mock_list):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_list.return_value = MagicMock(data=[{"id": "sub_1", "metadata": {"etablissement_id": "99"}}])

        result = check_existing_subscription_for_etablissement(user, 42)

        self.assertIsNone(result)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestCancelSubscription(TestCase):
    def test_returns_none_when_no_customer_id(self):
        user = UserFactory(stripe_customer_id=None)

        result = cancel_subscription_for_etablissement(user, 1)

        self.assertIsNone(result)

    @patch("apps.private.payments.services.stripe.Subscription.modify")
    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_cancels_at_period_end(self, mock_check, mock_modify):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {
            "id": "sub_1",
            "status": "active",
            "cancel_at_period_end": False,
        }
        mock_modify.return_value = {"id": "sub_1", "cancel_at_period_end": True}

        result = cancel_subscription_for_etablissement(user, 1)

        mock_modify.assert_called_once_with("sub_1", cancel_at_period_end=True)
        self.assertEqual(result["cancel_at_period_end"], True)

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_subscription_when_already_cancelled(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {"id": "sub_1", "status": "canceled"}

        result = cancel_subscription_for_etablissement(user, 1)

        self.assertEqual(result["id"], "sub_1")

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_none_when_no_subscription(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = None

        result = cancel_subscription_for_etablissement(user, 1)

        self.assertIsNone(result)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestSyncStripeData(TestCase):
    def test_skips_when_no_customer_id(self):
        user = UserFactory(stripe_customer_id=None)

        # Should not raise
        sync_stripe_data(user)

    @patch("apps.private.payments.services.stripe.Subscription.list")
    def test_activates_etablissement_for_active_subscription(self, mock_list):
        etab = EtablissementFactory(active=False)
        user = etab.google_credential.user
        user.stripe_customer_id = "cus_123"
        user.save(update_fields=["stripe_customer_id"])

        mock_sub = {
            "id": "sub_1",
            "status": "active",
            "metadata": {"etablissement_id": str(etab.id)},
            "cancel_at_period_end": False,
            "cancel_at": None,
            "created": 1700000000,
            "items": {"data": [{"price": {"id": "price_123"}}]},
        }
        mock_response = MagicMock()
        mock_response.data = [mock_sub]
        mock_response.has_more = False
        mock_list.return_value = mock_response

        sync_stripe_data(user)

        etab.refresh_from_db()
        self.assertTrue(etab.active)

    @patch("apps.private.payments.services.stripe.Subscription.list")
    def test_deactivates_etablissement_for_canceled_subscription(self, mock_list):
        etab = EtablissementFactory(active=True)
        user = etab.google_credential.user
        user.stripe_customer_id = "cus_123"
        user.save(update_fields=["stripe_customer_id"])

        mock_sub = {
            "id": "sub_1",
            "status": "canceled",
            "metadata": {"etablissement_id": str(etab.id)},
            "cancel_at_period_end": False,
            "cancel_at": None,
            "created": 1700000000,
            "items": {"data": [{"price": {"id": "price_123"}}]},
        }
        mock_response = MagicMock()
        mock_response.data = [mock_sub]
        mock_response.has_more = False
        mock_list.return_value = mock_response

        sync_stripe_data(user)

        etab.refresh_from_db()
        self.assertFalse(etab.active)

    @patch("apps.private.payments.services.stripe.Subscription.list")
    def test_deactivates_unprocessed_etablissements(self, mock_list):
        """Etablissements with no subscription should be deactivated."""
        cred = EtablissementFactory(active=True).google_credential
        user = cred.user
        user.stripe_customer_id = "cus_123"
        user.save(update_fields=["stripe_customer_id"])

        # Empty subscription list
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.has_more = False
        mock_list.return_value = mock_response

        sync_stripe_data(user)

        # The etablissement should be deactivated since it has no subscription
        etab = cred.etablissements.first()
        etab.refresh_from_db()
        self.assertFalse(etab.active)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestReactivateSubscription(TestCase):
    def test_returns_none_when_no_customer_id(self):
        user = UserFactory(stripe_customer_id=None)
        result = reactivate_subscription_for_etablissement(user, 1)
        self.assertIsNone(result)

    @patch("apps.private.payments.services.stripe.Subscription.modify")
    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_reactivates_scheduled_cancellation(self, mock_check, mock_modify):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {
            "id": "sub_1",
            "status": "active",
            "cancel_at_period_end": True,
        }
        mock_modify.return_value = {"id": "sub_1", "cancel_at_period_end": False}

        result = reactivate_subscription_for_etablissement(user, 1)

        mock_modify.assert_called_once_with("sub_1", cancel_at_period_end=False)
        self.assertFalse(result["cancel_at_period_end"])

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_none_when_already_canceled(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {"id": "sub_1", "status": "canceled"}

        result = reactivate_subscription_for_etablissement(user, 1)

        self.assertIsNone(result)

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_subscription_when_not_scheduled_for_cancel(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {
            "id": "sub_1",
            "status": "active",
            "cancel_at_period_end": False,
        }

        result = reactivate_subscription_for_etablissement(user, 1)

        self.assertEqual(result["id"], "sub_1")

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_none_when_no_subscription(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = None

        result = reactivate_subscription_for_etablissement(user, 1)

        self.assertIsNone(result)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestChangePlan(TestCase):
    def test_returns_none_when_no_customer_id(self):
        user = UserFactory(stripe_customer_id=None)
        result = change_plan_for_etablissement(user, 1, "price_new")
        self.assertIsNone(result)

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_none_when_no_subscription(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = None

        result = change_plan_for_etablissement(user, 1, "price_new")

        self.assertIsNone(result)

    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_returns_none_for_inactive_subscription(self, mock_check):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {"id": "sub_1", "status": "canceled"}

        result = change_plan_for_etablissement(user, 1, "price_new")

        self.assertIsNone(result)

    @patch("apps.private.payments.services._release_existing_schedule")
    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_cancels_schedule_when_same_plan(self, mock_check, mock_release):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {
            "id": "sub_1",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_current"}}]},
        }

        result = change_plan_for_etablissement(user, 1, "price_current")

        self.assertEqual(result, "cancelled")
        mock_release.assert_called_once()

    @patch("apps.private.payments.services.stripe.SubscriptionSchedule.modify")
    @patch("apps.private.payments.services.stripe.SubscriptionSchedule.create")
    @patch("apps.private.payments.services._release_existing_schedule")
    @patch("apps.private.payments.services.check_existing_subscription_for_etablissement")
    def test_creates_schedule_for_new_plan(self, mock_check, mock_release, mock_create, mock_modify):
        user = UserFactory(stripe_customer_id="cus_123")
        mock_check.return_value = {
            "id": "sub_1",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_current"}}]},
        }
        mock_schedule = MagicMock()
        mock_schedule.id = "sched_1"
        mock_schedule.phases = [{"start_date": 1000, "end_date": 2000}]
        mock_create.return_value = mock_schedule

        result = change_plan_for_etablissement(user, 1, "price_new")

        self.assertTrue(result)
        mock_create.assert_called_once()
        mock_modify.assert_called_once()


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestGetPendingPlanChange(TestCase):
    @patch("apps.private.payments.services.stripe.SubscriptionSchedule.list")
    def test_returns_pending_price_id(self, mock_list):
        mock_schedule = MagicMock()
        mock_schedule.subscription = "sub_1"
        mock_schedule.status = "active"
        mock_schedule.phases = [
            {"items": [{"price": "price_current"}]},
            {"items": [{"price": "price_new"}]},
        ]
        mock_list.return_value = MagicMock(data=[mock_schedule])

        result = get_pending_plan_change("sub_1", "cus_123")

        self.assertEqual(result, "price_new")

    @patch("apps.private.payments.services.stripe.SubscriptionSchedule.list")
    def test_returns_none_when_no_schedule(self, mock_list):
        mock_list.return_value = MagicMock(data=[])

        result = get_pending_plan_change("sub_1", "cus_123")

        self.assertIsNone(result)

    @patch("apps.private.payments.services.stripe.SubscriptionSchedule.list")
    def test_returns_none_when_single_phase(self, mock_list):
        mock_schedule = MagicMock()
        mock_schedule.subscription = "sub_1"
        mock_schedule.status = "active"
        mock_schedule.phases = [{"items": [{"price": "price_current"}]}]
        mock_list.return_value = MagicMock(data=[mock_schedule])

        result = get_pending_plan_change("sub_1", "cus_123")

        self.assertIsNone(result)

    @patch("apps.private.payments.services.stripe.SubscriptionSchedule.list")
    def test_returns_none_on_api_error(self, mock_list):
        mock_list.side_effect = Exception("Stripe API error")

        result = get_pending_plan_change("sub_1", "cus_123")

        self.assertIsNone(result)
