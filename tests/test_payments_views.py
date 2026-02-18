from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from tests.factories import EtablissementFactory, StripeSubscriptionFactory, UserFactory


@override_settings(STRIPE_SECRET_KEY="sk_test_fake", WEBSITE_URL="https://test.starshield.fr")
class TestCreateCheckoutSession(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

    def test_404_when_no_etablissement_in_session(self):
        session = self.client.session
        session["price_id"] = "price_123"
        session.save()

        response = self.client.get(reverse("payments:create_checkout_session"))

        self.assertEqual(response.status_code, 404)

    def test_404_when_no_price_id_in_session(self):
        session = self.client.session
        session["etablissement_id"] = self.etab.id
        session.save()

        response = self.client.get(reverse("payments:create_checkout_session"))

        self.assertEqual(response.status_code, 404)

    @patch("apps.private.payments.views.sync_stripe_data")
    @patch("apps.private.payments.views.check_existing_subscription_for_etablissement")
    def test_404_when_active_subscription_exists_in_db(self, mock_check, mock_sync):
        mock_check.return_value = None
        StripeSubscriptionFactory(etablissement=self.etab, status="active")
        session = self.client.session
        session["etablissement_id"] = self.etab.id
        session["price_id"] = "price_123"
        session.save()

        response = self.client.get(reverse("payments:create_checkout_session"))

        self.assertEqual(response.status_code, 404)

    @patch("apps.private.payments.views.stripe.checkout.Session.create")
    @patch("apps.private.payments.views.get_or_create_stripe_customer")
    @patch("apps.private.payments.views.check_existing_subscription_for_etablissement")
    def test_success_redirects_to_stripe(self, mock_check, mock_customer, mock_create):
        mock_check.return_value = None
        mock_customer.return_value = "cus_test"
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_123"
        mock_create.return_value = mock_session

        session = self.client.session
        session["etablissement_id"] = self.etab.id
        session["price_id"] = "price_123"
        session.save()

        response = self.client.get(reverse("payments:create_checkout_session"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("stripe.com", response.url)

    @patch("apps.private.payments.views.stripe.checkout.Session.create")
    @patch("apps.private.payments.views.get_or_create_stripe_customer")
    @patch("apps.private.payments.views.check_existing_subscription_for_etablissement")
    def test_stripe_error_raises(self, mock_check, mock_customer, mock_create):
        mock_check.return_value = None
        mock_customer.return_value = "cus_test"
        mock_create.side_effect = Exception("Stripe error")

        session = self.client.session
        session["etablissement_id"] = self.etab.id
        session["price_id"] = "price_123"
        session.save()

        with self.assertRaises(Exception):  # noqa: B017
            self.client.get(reverse("payments:create_checkout_session"))

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("payments:create_checkout_session"))
        self.assertEqual(response.status_code, 302)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake", LOGIN_REDIRECT_URL="/dashboard/")
class TestCheckoutSuccess(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)

    @patch("apps.private.payments.views.sync_stripe_data")
    def test_with_etablissement_id_redirects_to_list(self, mock_sync):
        response = self.client.get(reverse("payments:checkout_success"), {"etablissement_id": "42"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("etablissements", response.url)
        mock_sync.assert_called_once()

    @patch("apps.private.payments.views.sync_stripe_data")
    def test_without_etablissement_id_redirects_to_dashboard(self, mock_sync):
        response = self.client.get(reverse("payments:checkout_success"))

        self.assertEqual(response.status_code, 302)
        mock_sync.assert_called_once()


@override_settings(STRIPE_SECRET_KEY="sk_test_fake")
class TestCheckoutCancel(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_redirects_to_accueil(self):
        response = self.client.get(reverse("payments:checkout_cancel"))

        self.assertEqual(response.status_code, 302)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake", WEBSITE_URL="https://test.starshield.fr")
class TestStripeCustomerPortal(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)

    @patch("apps.private.payments.views.stripe.billing_portal.Session.create")
    @patch("apps.private.payments.views.get_or_create_stripe_customer")
    def test_redirects_to_portal(self, mock_customer, mock_portal):
        mock_customer.return_value = "cus_test"
        mock_portal_session = MagicMock()
        mock_portal_session.url = "https://billing.stripe.com/portal"
        mock_portal.return_value = mock_portal_session

        response = self.client.post(reverse("payments:stripe_customer_portal"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("stripe.com", response.url)

    def test_requires_post(self):
        response = self.client.get(reverse("payments:stripe_customer_portal"))
        self.assertEqual(response.status_code, 405)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("payments:stripe_customer_portal"))
        self.assertEqual(response.status_code, 302)
