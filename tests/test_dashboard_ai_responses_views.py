from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from tests.factories import EtablissementFactory, ReviewFactory


class DashboardAiResponsesMixin:
    def setUp(self):
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()


class TestAiResponsesSettingsView(DashboardAiResponsesMixin, TestCase):
    def test_get_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_post_saves_settings(self):
        response = self.client.post(
            reverse("dashboard:etablissement:ai_responses:settings"),
            data={
                "ai_response_tone": "enthousiaste",
                "ai_response_length": "long",
                "ai_response_language": "en",
                "ai_response_validation_required": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.etab.refresh_from_db()
        self.assertEqual(self.etab.ai_response_tone, "enthousiaste")
        self.assertEqual(self.etab.ai_response_length, "long")
        self.assertEqual(self.etab.ai_response_language, "en")
        self.assertTrue(self.etab.ai_response_validation_required)

    def test_post_invalid_data_rerenders(self):
        response = self.client.post(
            reverse("dashboard:etablissement:ai_responses:settings"),
            data={
                "ai_response_tone": "invalid",
                "ai_response_length": "medium",
                "ai_response_language": "fr",
            },
        )
        self.assertEqual(response.status_code, 200)


class TestAiResponsesPreviewView(DashboardAiResponsesMixin, TestCase):
    def test_get_default_preview(self):
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:preview"))
        self.assertEqual(response.status_code, 200)

    def test_get_preview_with_params(self):
        response = self.client.get(
            reverse("dashboard:etablissement:ai_responses:preview"),
            {
                "ai_response_tone": "empathique",
                "ai_response_length": "short",
                "ai_response_language": "en",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_auto_language_shows_french(self):
        response = self.client.get(
            reverse("dashboard:etablissement:ai_responses:preview"),
            {"ai_response_language": "auto"},
        )
        self.assertEqual(response.status_code, 200)


class TestAiResponsesHistoriqueView(DashboardAiResponsesMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:historique"))
        self.assertEqual(response.status_code, 200)


class TestAiResponsesHistoriqueContentPartial(DashboardAiResponsesMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:historique_content"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("stats", response.context)
        self.assertIn("table_data", response.context)

    def test_with_replied_reviews(self):
        from django.utils import timezone

        ReviewFactory(
            etablissement=self.etab,
            source="google",
            reply_comment="Merci !",
            reply_type="ai",
            reply_date=timezone.now(),
        )
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:historique_content"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["table_data"]["rows"]), 1)

    def test_period_filter_all(self):
        response = self.client.get(
            reverse("dashboard:etablissement:ai_responses:historique_content"),
            {"period": "all"},
        )
        self.assertEqual(response.status_code, 200)


class TestPendingView(DashboardAiResponsesMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:pending"))
        self.assertEqual(response.status_code, 200)


class TestPendingContentPartial(DashboardAiResponsesMixin, TestCase):
    def test_returns_200_no_pending(self):
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:pending_content"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get("review"))

    def test_returns_pending_review(self):
        review = ReviewFactory(
            etablissement=self.etab,
            source="google",
            ai_response_status="pending",
            ai_draft_comment="Draft response",
        )
        response = self.client.get(reverse("dashboard:etablissement:ai_responses:pending_content"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["review"].id, review.id)


class TestApproveReviewView(DashboardAiResponsesMixin, TestCase):
    def _create_pending_review(self):
        return ReviewFactory(
            etablissement=self.etab,
            source="google",
            ai_response_status="pending",
            ai_draft_comment="Draft",
        )

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.approve_ai_response")
    def test_approve_success(self, mock_approve):
        mock_approve.return_value = True
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_approve", args=[review.id])
        response = self.client.post(url, data={"edited_comment": "Merci !"})
        self.assertEqual(response.status_code, 200)
        mock_approve.assert_called_once_with(review.id, edited_comment="Merci !")

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.approve_ai_response")
    def test_approve_without_edit(self, mock_approve):
        mock_approve.return_value = True
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_approve", args=[review.id])
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 200)
        mock_approve.assert_called_once_with(review.id, edited_comment=None)

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.approve_ai_response")
    def test_approve_failure(self, mock_approve):
        mock_approve.return_value = False
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_approve", args=[review.id])
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 200)

    def test_approve_nonexistent_review_404(self):
        url = reverse("dashboard:etablissement:ai_responses:pending_approve", args=[99999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_approve_requires_post(self):
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_approve", args=[review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class TestRejectReviewView(DashboardAiResponsesMixin, TestCase):
    def _create_pending_review(self):
        return ReviewFactory(
            etablissement=self.etab,
            source="google",
            ai_response_status="pending",
            ai_draft_comment="Draft",
        )

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.reject_ai_response")
    def test_reject_success(self, mock_reject):
        mock_reject.return_value = True
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_reject", args=[review.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        mock_reject.assert_called_once_with(review.id)

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.reject_ai_response")
    def test_reject_failure(self, mock_reject):
        mock_reject.return_value = False
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_reject", args=[review.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_reject_nonexistent_404(self):
        url = reverse("dashboard:etablissement:ai_responses:pending_reject", args=[99999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class TestRegenerateReviewView(DashboardAiResponsesMixin, TestCase):
    def _create_pending_review(self):
        return ReviewFactory(
            etablissement=self.etab,
            source="google",
            ai_response_status="pending",
            ai_draft_comment="Draft",
        )

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.regenerate_ai_response")
    def test_regenerate_success(self, mock_regen):
        mock_regen.return_value = "New draft response"
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_regenerate", args=[review.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        mock_regen.assert_called_once_with(review.id)

    @patch("apps.private.dashboard.views.etablissement.ai_responses.pending.regenerate_ai_response")
    def test_regenerate_failure(self, mock_regen):
        mock_regen.return_value = None
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_regenerate", args=[review.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_regenerate_nonexistent_404(self):
        url = reverse("dashboard:etablissement:ai_responses:pending_regenerate", args=[99999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_regenerate_requires_post(self):
        review = self._create_pending_review()
        url = reverse("dashboard:etablissement:ai_responses:pending_regenerate", args=[review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
