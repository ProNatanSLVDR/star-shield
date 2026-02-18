from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.private.auths.models import Etablissement
from tests.factories import EtablissementFactory, StripeSubscriptionFactory


class DashboardEtablissementsMixin:
    """Shared setUp for etablissements views."""

    def setUp(self):
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)


class TestListEtablissementsView(DashboardEtablissementsMixin, TestCase):
    def test_full_page_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissements:list"))
        self.assertEqual(response.status_code, 200)

    def test_htmx_returns_partial(self):
        response = self.client.get(
            reverse("dashboard:etablissements:list"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("etablissements_table", response.context)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:etablissements:list"))
        self.assertEqual(response.status_code, 302)


class TestEtablissementDetailsPartial(DashboardEtablissementsMixin, TestCase):
    @patch("apps.private.dashboard.views.etablissements.views.check_existing_subscription_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    def test_get_returns_200(self, mock_sub_state, mock_check_sub):
        mock_sub_state.return_value = {"subscription": None, "state": "inactive"}
        url = reverse("dashboard:etablissements:details_partial", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("etablissement", response.context)

    @patch("apps.private.dashboard.views.etablissements.views.check_existing_subscription_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    def test_post_saves_settings(self, mock_sub_state, mock_check_sub):
        mock_sub_state.return_value = {"subscription": None, "state": "inactive"}
        url = reverse("dashboard:etablissements:details_partial", args=[self.etab.id])
        response = self.client.post(url, data={"title": "Nouveau Nom", "target_rating": "4.50"})
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertEqual(self.etab.title, "Nouveau Nom")

    def test_other_user_cannot_access(self):
        other_etab = EtablissementFactory(active=True)
        url = reverse("dashboard:etablissements:details_partial", args=[other_etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestSelectEtablissement(DashboardEtablissementsMixin, TestCase):
    def test_select_stores_in_session(self):
        url = reverse("dashboard:etablissements:select", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["selected_etablissement"], self.etab.id)

    def test_select_nonexistent_redirects_with_error(self):
        url = reverse("dashboard:etablissements:select", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("selected_etablissement", self.client.session)

    def test_cannot_select_other_users_etablissement(self):
        other_etab = EtablissementFactory(active=True)
        url = reverse("dashboard:etablissements:select", args=[other_etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("selected_etablissement", self.client.session)


class TestUnselectEtablissement(DashboardEtablissementsMixin, TestCase):
    def test_unselect_clears_session(self):
        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()

        response = self.client.get(reverse("dashboard:etablissements:unselect"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("selected_etablissement", self.client.session)


class TestDeleteEtablissementPartial(DashboardEtablissementsMixin, TestCase):
    def test_get_active_etab_shows_error(self):
        url = reverse("dashboard:etablissements:delete_partial", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Active etab cannot be deleted
        self.assertIsNone(response.context.get("delete_url"))

    def test_get_inactive_etab_shows_confirmation(self):
        self.etab.active = False
        self.etab.save()
        url = reverse("dashboard:etablissements:delete_partial", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get("delete_url"))

    def test_post_inactive_etab_deletes(self):
        self.etab.active = False
        self.etab.save()
        url = reverse("dashboard:etablissements:delete_partial", args=[self.etab.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Etablissement.objects.filter(id=self.etab.id).exists())

    def test_post_active_etab_blocks_deletion(self):
        url = reverse("dashboard:etablissements:delete_partial", args=[self.etab.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Etablissement.objects.filter(id=self.etab.id).exists())

    def test_nonexistent_etab(self):
        url = reverse("dashboard:etablissements:delete_partial", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestToggleEtablissementStatus(DashboardEtablissementsMixin, TestCase):
    @patch("apps.private.dashboard.views.etablissements.views.check_existing_subscription_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    @patch("apps.private.dashboard.views.etablissements.views.get_stripe_prices")
    def test_toggle_status_partial_inactive_no_sub(self, mock_prices, mock_sub_state, mock_check_sub):
        self.etab.active = False
        self.etab.save()
        mock_sub_state.return_value = {"subscription": None, "state": "inactive"}
        mock_prices.return_value = {
            "monthly": {"id": "price_m", "amount": 999},
            "trimestrial": {"id": "price_t", "amount": 2499},
            "yearly": {"id": "price_y", "amount": 8999},
        }
        url = reverse("dashboard:etablissements:toggle_status_partial", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_activation"])

    @patch("apps.private.dashboard.views.etablissements.views.cancel_subscription_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.sync_stripe_data")
    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    def test_toggle_deactivate_active_with_sub(self, mock_sub_state, mock_sync, mock_cancel):
        mock_sub_state.return_value = {"subscription": StripeSubscriptionFactory(etablissement=self.etab), "state": "active"}
        self.etab.active = True
        self.etab.save()
        url = reverse("dashboard:etablissements:toggle_status", args=[self.etab.id])
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])
        mock_cancel.assert_called_once()

    @patch("apps.private.dashboard.views.etablissements.views.reactivate_subscription_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.sync_stripe_data")
    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    def test_toggle_reactivate(self, mock_sub_state, mock_sync, mock_reactivate):
        mock_sub_state.return_value = {
            "subscription": StripeSubscriptionFactory(etablissement=self.etab, cancel_at_period_end=True),
            "state": "cancellation_pending",
        }
        mock_reactivate.return_value = True
        url = reverse("dashboard:etablissements:toggle_status", args=[self.etab.id])
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])
        mock_reactivate.assert_called_once()

    def test_toggle_requires_post(self):
        url = reverse("dashboard:etablissements:toggle_status", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class TestChangePlan(DashboardEtablissementsMixin, TestCase):
    @patch("apps.private.dashboard.views.etablissements.views.get_pending_plan_change")
    @patch("apps.private.dashboard.views.etablissements.views.check_existing_subscription_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.get_stripe_prices")
    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    def test_change_plan_partial_active_sub(self, mock_sub_state, mock_prices, mock_check_sub, mock_pending):
        sub = StripeSubscriptionFactory(etablissement=self.etab)
        mock_sub_state.return_value = {"subscription": sub, "state": "active"}
        mock_prices.return_value = {
            "monthly": {"id": "price_m", "amount": 999},
            "trimestrial": {"id": "price_t", "amount": 2499},
            "yearly": {"id": "price_y", "amount": 8999},
        }
        mock_check_sub.return_value = {"id": "sub_123"}
        mock_pending.return_value = None
        url = reverse("dashboard:etablissements:change_plan_partial", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("prices", response.context)

    @patch("apps.private.dashboard.views.etablissements.views.get_subscription_state")
    def test_change_plan_partial_no_sub(self, mock_sub_state):
        mock_sub_state.return_value = {"subscription": None, "state": "inactive"}
        url = reverse("dashboard:etablissements:change_plan_partial", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @patch("apps.private.dashboard.views.etablissements.views.change_plan_for_etablissement")
    @patch("apps.private.dashboard.views.etablissements.views.sync_stripe_data")
    def test_change_plan_post_success(self, mock_sync, mock_change):
        mock_change.return_value = True

        url = reverse("dashboard:etablissements:change_plan", args=[self.etab.id])
        with patch(
            "apps.private.dashboard.views.etablissements.forms.settings"
        ) as mock_settings:
            mock_settings.STRIPE_PRODUCTS = {
                "basic_subscription": {
                    "monthly": "price_m",
                    "trimestrial": "price_t",
                    "yearly": "price_y",
                }
            }
            response = self.client.post(url, data={"price_id": "price_m"})

        self.assertIn(response.status_code, [200, 302])
        mock_change.assert_called_once()

    def test_change_plan_requires_post(self):
        url = reverse("dashboard:etablissements:change_plan", args=[self.etab.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class TestEtablissementSelectorPartial(DashboardEtablissementsMixin, TestCase):
    def test_returns_200_with_valid_credential(self):
        response = self.client.get(reverse("dashboard:etablissements:selector_partial"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("etablissements_table", response.context)

    def test_invalid_credential_shows_error(self):
        cred = self.user.google_credential
        cred.is_valid = False
        cred.save()
        response = self.client.get(reverse("dashboard:etablissements:selector_partial"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("error"))

    def test_invalid_grants_shows_error(self):
        cred = self.user.google_credential
        cred.has_invalid_grants = True
        cred.save()
        response = self.client.get(reverse("dashboard:etablissements:selector_partial"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("error"))
