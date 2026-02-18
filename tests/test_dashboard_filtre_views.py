from django.test import TestCase
from django.urls import reverse

from tests.factories import EtablissementFactory, RatingHistoryFactory


class DashboardFiltreMixin:
    def setUp(self):
        self.etab = EtablissementFactory(active=True, target_rating=4.50)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()


class TestThresholdSettingsView(DashboardFiltreMixin, TestCase):
    def test_get_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:filtre:threshold"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_get_with_rating_history(self):
        RatingHistoryFactory(etablissement=self.etab, rating=4.2, total_reviews=50)
        response = self.client.get(reverse("dashboard:etablissement:filtre:threshold"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_rating"], 4.2)
        self.assertEqual(response.context["total_reviews"], 50)

    def test_post_updates_threshold(self):
        response = self.client.post(
            reverse("dashboard:etablissement:filtre:threshold"),
            data={"review_threshold": "5"},
        )
        self.assertEqual(response.status_code, 302)
        self.etab.refresh_from_db()
        self.assertEqual(self.etab.review_threshold, 5)

    def test_post_valid_threshold_3(self):
        response = self.client.post(
            reverse("dashboard:etablissement:filtre:threshold"),
            data={"review_threshold": "3"},
        )
        self.assertEqual(response.status_code, 302)
        self.etab.refresh_from_db()
        self.assertEqual(self.etab.review_threshold, 3)

    def test_post_invalid_threshold(self):
        response = self.client.post(
            reverse("dashboard:etablissement:filtre:threshold"),
            data={"review_threshold": "2"},
        )
        self.assertEqual(response.status_code, 200)  # Re-renders form


class TestPersonalisationSettingsView(DashboardFiltreMixin, TestCase):
    def test_get_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:filtre:personalisation"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("preview_context", response.context)

    def test_post_saves_settings(self):
        response = self.client.post(
            reverse("dashboard:etablissement:filtre:personalisation"),
            data={
                "review_accent_color": "#FF5733",
                "review_show_etablissement_pill": "True",
                "review_page_label": "Votre avis",
                "review_page_text": "Merci de votre visite",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.etab.refresh_from_db()
        self.assertEqual(self.etab.review_accent_color, "#FF5733")
        self.assertEqual(self.etab.review_page_label, "Votre avis")

    def test_post_invalid_hex_color(self):
        response = self.client.post(
            reverse("dashboard:etablissement:filtre:personalisation"),
            data={"review_accent_color": "not-a-color"},
        )
        self.assertEqual(response.status_code, 200)

    def test_post_empty_optional_fields(self):
        response = self.client.post(
            reverse("dashboard:etablissement:filtre:personalisation"),
            data={
                "review_accent_color": "#000000",
                "review_show_etablissement_pill": "True",
                "review_page_label": "",
                "review_page_text": "",
            },
        )
        self.assertEqual(response.status_code, 302)


class TestPersonalisationPreviewView(DashboardFiltreMixin, TestCase):
    def test_default_preview(self):
        response = self.client.get(reverse("dashboard:etablissement:filtre:personalisation_preview"))
        self.assertEqual(response.status_code, 200)

    def test_preview_with_params(self):
        response = self.client.get(
            reverse("dashboard:etablissement:filtre:personalisation_preview"),
            {
                "review_accent_color": "#FF0000",
                "review_show_etablissement_pill": "False",
                "review_page_label": "Custom label",
                "review_page_text": "Custom text",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_unsaved_changes_detection(self):
        response = self.client.get(
            reverse("dashboard:etablissement:filtre:personalisation_preview"),
            {"review_accent_color": "#AABBCC"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("has_unsaved_changes"))

    def test_no_unsaved_changes(self):
        response = self.client.get(
            reverse("dashboard:etablissement:filtre:personalisation_preview"),
            {
                "review_accent_color": self.etab.review_accent_color,
                "review_show_etablissement_pill": str(self.etab.review_show_etablissement_pill),
                "review_page_label": self.etab.review_page_label or "",
                "review_page_text": self.etab.review_page_text or "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get("has_unsaved_changes"))
