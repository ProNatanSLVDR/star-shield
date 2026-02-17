from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.private.payments.helpers import get_plan_label, get_price_id_map, get_stripe_prices, get_subscription_state
from tests.factories import EtablissementFactory, StripeSubscriptionFactory

TEST_STRIPE_PRODUCTS = {
    "basic_subscription": {
        "product_id": "prod_test",
        "monthly": "price_monthly",
        "trimestrial": "price_trimestrial",
        "yearly": "price_yearly",
    }
}


@override_settings(STRIPE_PRODUCTS=TEST_STRIPE_PRODUCTS)
class TestGetPriceIdMap(TestCase):
    def test_returns_basic_subscription_map(self):
        result = get_price_id_map()

        self.assertEqual(result["monthly"], "price_monthly")
        self.assertEqual(result["trimestrial"], "price_trimestrial")
        self.assertEqual(result["yearly"], "price_yearly")

    @override_settings(STRIPE_PRODUCTS={})
    def test_returns_empty_dict_when_no_config(self):
        result = get_price_id_map()

        self.assertEqual(result, {})


@override_settings(STRIPE_PRODUCTS=TEST_STRIPE_PRODUCTS)
class TestGetPlanLabel(TestCase):
    def test_monthly(self):
        self.assertEqual(get_plan_label("price_monthly"), "Mensuel")

    def test_trimestrial(self):
        self.assertEqual(get_plan_label("price_trimestrial"), "Trimestriel")

    def test_yearly(self):
        self.assertEqual(get_plan_label("price_yearly"), "Annuel")

    def test_unknown_price_id(self):
        self.assertEqual(get_plan_label("price_unknown"), "")

    def test_none_price_id(self):
        self.assertEqual(get_plan_label(None), "")

    def test_empty_string_price_id(self):
        self.assertEqual(get_plan_label(""), "")


class TestGetSubscriptionState(TestCase):
    def test_inactive_when_no_subscription(self):
        etab = EtablissementFactory(active=False)

        result = get_subscription_state(etab)

        self.assertIsNone(result["subscription"])
        self.assertEqual(result["state"], "inactive")

    def test_active_with_active_subscription(self):
        etab = EtablissementFactory(active=True)
        sub = StripeSubscriptionFactory(etablissement=etab, status="active", cancel_at_period_end=False)

        result = get_subscription_state(etab)

        self.assertEqual(result["subscription"].id, sub.id)
        self.assertEqual(result["state"], "active")

    def test_cancellation_pending(self):
        etab = EtablissementFactory(active=True)
        sub = StripeSubscriptionFactory(etablissement=etab, status="active", cancel_at_period_end=True)

        result = get_subscription_state(etab)

        self.assertEqual(result["subscription"].id, sub.id)
        self.assertEqual(result["state"], "cancellation_pending")

    def test_inactive_when_subscription_active_but_etablissement_inactive(self):
        etab = EtablissementFactory(active=False)
        StripeSubscriptionFactory(etablissement=etab, status="active", cancel_at_period_end=False)

        result = get_subscription_state(etab)

        self.assertIsNotNone(result["subscription"])
        self.assertEqual(result["state"], "inactive")

    def test_inactive_when_subscription_canceled(self):
        etab = EtablissementFactory(active=False)
        StripeSubscriptionFactory(etablissement=etab, status="canceled")

        result = get_subscription_state(etab)

        self.assertIsNone(result["subscription"])
        self.assertEqual(result["state"], "inactive")

    def test_trialing_subscription_is_active(self):
        etab = EtablissementFactory(active=True)
        sub = StripeSubscriptionFactory(etablissement=etab, status="trialing", cancel_at_period_end=False)

        result = get_subscription_state(etab)

        self.assertEqual(result["subscription"].id, sub.id)
        self.assertEqual(result["state"], "active")


@override_settings(STRIPE_PRODUCTS=TEST_STRIPE_PRODUCTS, STRIPE_SECRET_KEY="sk_test_fake")
class TestGetStripePrices(TestCase):
    @patch("apps.private.payments.helpers.stripe.Price.retrieve")
    def test_fetches_all_three_prices(self, mock_retrieve):
        def side_effect(price_id):
            prices = {
                "price_monthly": MagicMock(unit_amount=1000, currency="eur"),
                "price_trimestrial": MagicMock(unit_amount=2700, currency="eur"),
                "price_yearly": MagicMock(unit_amount=9600, currency="eur"),
            }
            return prices[price_id]

        mock_retrieve.side_effect = side_effect

        result = get_stripe_prices()

        self.assertEqual(result["monthly"]["amount"], 10.0)
        self.assertEqual(result["trimestrial"]["amount"], 27.0)
        self.assertEqual(result["yearly"]["amount"], 96.0)
        self.assertEqual(mock_retrieve.call_count, 3)

    @patch("apps.private.payments.helpers.stripe.Price.retrieve")
    def test_calculates_trimestrial_savings(self, mock_retrieve):
        def side_effect(price_id):
            prices = {
                "price_monthly": MagicMock(unit_amount=1000, currency="eur"),
                "price_trimestrial": MagicMock(unit_amount=2700, currency="eur"),
                "price_yearly": MagicMock(unit_amount=9600, currency="eur"),
            }
            return prices[price_id]

        mock_retrieve.side_effect = side_effect

        result = get_stripe_prices()

        # 3 * 10 = 30, savings = (30 - 27) / 30 * 100 = 10%
        self.assertEqual(result["trimestrial"]["full_price"], 30.0)
        self.assertEqual(result["trimestrial"]["savings_percent"], 10)

    @patch("apps.private.payments.helpers.stripe.Price.retrieve")
    def test_calculates_yearly_savings(self, mock_retrieve):
        def side_effect(price_id):
            prices = {
                "price_monthly": MagicMock(unit_amount=1000, currency="eur"),
                "price_trimestrial": MagicMock(unit_amount=2700, currency="eur"),
                "price_yearly": MagicMock(unit_amount=9600, currency="eur"),
            }
            return prices[price_id]

        mock_retrieve.side_effect = side_effect

        result = get_stripe_prices()

        # 12 * 10 = 120, savings = (120 - 96) / 120 * 100 = 20%
        self.assertEqual(result["yearly"]["full_price"], 120.0)
        self.assertEqual(result["yearly"]["savings_percent"], 20)

    @patch("apps.private.payments.helpers.stripe.Price.retrieve")
    def test_handles_stripe_api_error(self, mock_retrieve):
        mock_retrieve.side_effect = Exception("Stripe API error")

        result = get_stripe_prices()

        self.assertIsNone(result["monthly"])
        self.assertIsNone(result["trimestrial"])
        self.assertIsNone(result["yearly"])

    @override_settings(STRIPE_PRODUCTS={"basic_subscription": {}})
    def test_handles_missing_price_ids(self):
        result = get_stripe_prices()

        self.assertIsNone(result["monthly"])
        self.assertIsNone(result["trimestrial"])
        self.assertIsNone(result["yearly"])

    @patch("apps.private.payments.helpers.stripe.Price.retrieve")
    def test_currency_uppercased(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(unit_amount=1000, currency="eur")

        result = get_stripe_prices()

        self.assertEqual(result["monthly"]["currency"], "EUR")

    @patch("apps.private.payments.helpers.stripe.Price.retrieve")
    def test_no_savings_when_monthly_fails(self, mock_retrieve):
        def side_effect(price_id):
            if price_id == "price_monthly":
                raise Exception("Stripe error")
            return MagicMock(unit_amount=2700, currency="eur")

        mock_retrieve.side_effect = side_effect

        result = get_stripe_prices()

        self.assertIsNone(result["monthly"])
        self.assertNotIn("savings_percent", result["trimestrial"])
