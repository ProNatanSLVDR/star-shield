from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from tests.factories import EtablissementFactory, GoogleCredentialsFactory, UserFactory


class TestOnboardingStepViews(TestCase):
    """Test that each onboarding step returns 200 for non-completed users."""

    def setUp(self):
        self.user = UserFactory(onboarding_completed=False)
        self.client.force_login(self.user)

    def test_welcome_returns_200(self):
        response = self.client.get(reverse("dashboard:onboarding:welcome"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 1)

    def test_how_it_works_returns_200(self):
        response = self.client.get(reverse("dashboard:onboarding:how_it_works"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 2)

    def test_threshold_returns_200(self):
        response = self.client.get(reverse("dashboard:onboarding:threshold"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 3)

    def test_roulette_returns_200(self):
        response = self.client.get(reverse("dashboard:onboarding:roulette"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 4)

    def test_ai_responses_returns_200(self):
        response = self.client.get(reverse("dashboard:onboarding:ai_responses"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 5)

    def test_connect_google_returns_200(self):
        response = self.client.get(reverse("dashboard:onboarding:connect_google"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 6)


class TestOnboardingCompletedRedirect(TestCase):
    """Test that completed users are redirected away from onboarding."""

    def setUp(self):
        self.user = UserFactory(onboarding_completed=True)
        self.client.force_login(self.user)

    def test_welcome_redirects(self):
        response = self.client.get(reverse("dashboard:onboarding:welcome"))
        self.assertEqual(response.status_code, 302)

    def test_how_it_works_redirects(self):
        response = self.client.get(reverse("dashboard:onboarding:how_it_works"))
        self.assertEqual(response.status_code, 302)

    def test_threshold_redirects(self):
        response = self.client.get(reverse("dashboard:onboarding:threshold"))
        self.assertEqual(response.status_code, 302)

    def test_complete_redirects(self):
        response = self.client.get(reverse("dashboard:onboarding:complete"))
        self.assertEqual(response.status_code, 302)


class TestConnectGoogleView(TestCase):
    def setUp(self):
        self.user = UserFactory(onboarding_completed=False)
        self.client.force_login(self.user)

    def test_no_credential_shows_connect(self):
        response = self.client.get(reverse("dashboard:onboarding:connect_google"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["has_google_connected"])
        self.assertIsNone(response.context["next_url"])

    def test_valid_credential_shows_next(self):
        GoogleCredentialsFactory(user=self.user, is_valid=True)
        response = self.client.get(reverse("dashboard:onboarding:connect_google"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["has_google_connected"])
        self.assertIsNotNone(response.context["next_url"])


class TestImportEtablissementsView(TestCase):
    def setUp(self):
        self.user = UserFactory(onboarding_completed=False)
        self.cred = GoogleCredentialsFactory(user=self.user, is_valid=True)
        self.client.force_login(self.user)

    def test_no_google_credential_redirects(self):
        self.cred.is_valid = False
        self.cred.save()
        response = self.client.get(reverse("dashboard:onboarding:import_etablissements"))
        self.assertEqual(response.status_code, 302)

    @patch(
        "apps.private.auths.models.GoogleCredentials.list_available_locations",
        return_value=[
            {"name": "loc/1", "title": "Shop 1", "exists": False, "account_id": "acc/1"},
        ],
    )
    def test_get_lists_locations(self, mock_locations):
        response = self.client.get(reverse("dashboard:onboarding:import_etablissements"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("available_locations", response.context)


class TestCompleteView(TestCase):
    def setUp(self):
        self.user = UserFactory(onboarding_completed=False)
        self.client.force_login(self.user)

    def test_marks_onboarding_completed(self):
        response = self.client.get(reverse("dashboard:onboarding:complete"))
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarding_completed)

    def test_already_completed_redirects(self):
        self.user.onboarding_completed = True
        self.user.save()
        response = self.client.get(reverse("dashboard:onboarding:complete"))
        self.assertEqual(response.status_code, 302)


class TestSkipOnboardingView(TestCase):
    def setUp(self):
        self.user = UserFactory(onboarding_completed=False)
        self.client.force_login(self.user)

    def test_skip_marks_completed(self):
        response = self.client.get(reverse("dashboard:onboarding:skip"))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarding_completed)

    def test_already_completed_redirects(self):
        self.user.onboarding_completed = True
        self.user.save()
        response = self.client.get(reverse("dashboard:onboarding:skip"))
        self.assertEqual(response.status_code, 302)


class TestReconnectGoogleView(TestCase):
    def setUp(self):
        self.user = UserFactory(onboarding_completed=True)
        self.client.force_login(self.user)

    def test_no_credential_shows_missing(self):
        response = self.client.get(reverse("dashboard:onboarding:reconnect_google"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["reason"], "missing")

    def test_invalid_grants_shows_reason(self):
        GoogleCredentialsFactory(user=self.user, is_valid=True, has_invalid_grants=True)
        response = self.client.get(reverse("dashboard:onboarding:reconnect_google"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["reason"], "invalid_grants")

    def test_expired_shows_reason(self):
        GoogleCredentialsFactory(user=self.user, is_valid=False, has_invalid_grants=False)
        response = self.client.get(reverse("dashboard:onboarding:reconnect_google"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["reason"], "expired")

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:onboarding:reconnect_google"))
        self.assertEqual(response.status_code, 302)
