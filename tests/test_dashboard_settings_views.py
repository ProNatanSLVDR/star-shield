from django.test import TestCase
from django.urls import reverse

from tests.factories import EtablissementFactory


class DashboardSettingsMixin:
    def setUp(self):
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()


class TestToggleFeatureView(DashboardSettingsMixin, TestCase):
    def test_toggle_all_features_on(self):
        self.etab.review_filtering_enabled = False
        self.etab.roulette_enabled = False
        self.etab.ai_responses_enabled = False
        self.etab.save()

        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_feature"),
            data={
                "review_filtering_enabled": "on",
                "roulette_enabled": "on",
                "ai_responses_enabled": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertTrue(self.etab.review_filtering_enabled)
        self.assertTrue(self.etab.roulette_enabled)
        self.assertTrue(self.etab.ai_responses_enabled)

    def test_toggle_all_features_off(self):
        self.etab.review_filtering_enabled = True
        self.etab.roulette_enabled = True
        self.etab.ai_responses_enabled = True
        self.etab.save()

        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_feature"),
            data={},
        )
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertFalse(self.etab.review_filtering_enabled)
        self.assertFalse(self.etab.roulette_enabled)
        self.assertFalse(self.etab.ai_responses_enabled)

    def test_requires_post(self):
        response = self.client.get(reverse("dashboard:etablissement:settings:toggle_feature"))
        self.assertEqual(response.status_code, 405)


class TestToggleSingleFeatureView(DashboardSettingsMixin, TestCase):
    def test_toggle_roulette_on(self):
        self.etab.roulette_enabled = False
        self.etab.save()
        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_single_feature"),
            data={"feature": "roulette_enabled"},
        )
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertTrue(self.etab.roulette_enabled)

    def test_toggle_roulette_off(self):
        self.etab.roulette_enabled = True
        self.etab.save()
        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_single_feature"),
            data={"feature": "roulette_enabled"},
        )
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertFalse(self.etab.roulette_enabled)

    def test_toggle_ai_responses(self):
        self.etab.ai_responses_enabled = False
        self.etab.save()
        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_single_feature"),
            data={"feature": "ai_responses_enabled"},
        )
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertTrue(self.etab.ai_responses_enabled)

    def test_toggle_review_filtering(self):
        self.etab.review_filtering_enabled = False
        self.etab.save()
        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_single_feature"),
            data={"feature": "review_filtering_enabled"},
        )
        self.assertEqual(response.status_code, 200)
        self.etab.refresh_from_db()
        self.assertTrue(self.etab.review_filtering_enabled)

    def test_invalid_feature_returns_400(self):
        response = self.client.post(
            reverse("dashboard:etablissement:settings:toggle_single_feature"),
            data={"feature": "invalid_feature"},
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_post(self):
        response = self.client.get(reverse("dashboard:etablissement:settings:toggle_single_feature"))
        self.assertEqual(response.status_code, 405)
