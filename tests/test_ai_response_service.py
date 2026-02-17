from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.tasks_api.services.ai_response_service import (
    RATING_CONTEXT,
    _build_system_prompt,
    _build_user_prompt,
    _check_malicious,
    _get_rating_context,
    _get_unreplied_reviews,
    approve_ai_response,
    generate_and_send_responses,
    regenerate_ai_response,
    reject_ai_response,
)
from tests.factories import EtablissementFactory, ReviewFactory


class TestGetRatingContext(TestCase):
    def test_rating_1_returns_low(self):
        self.assertEqual(_get_rating_context(1), RATING_CONTEXT["low"])

    def test_rating_2_returns_low(self):
        self.assertEqual(_get_rating_context(2), RATING_CONTEXT["low"])

    def test_rating_3_returns_mid(self):
        self.assertEqual(_get_rating_context(3), RATING_CONTEXT["mid"])

    def test_rating_4_returns_high(self):
        self.assertEqual(_get_rating_context(4), RATING_CONTEXT["high"])

    def test_rating_5_returns_high(self):
        self.assertEqual(_get_rating_context(5), RATING_CONTEXT["high"])


class TestBuildSystemPrompt(TestCase):
    def test_includes_tone_instruction(self):
        etab = EtablissementFactory(ai_response_tone="empathique", title="Mon Resto")
        prompt = _build_system_prompt(etab)
        self.assertIn("empathiques", prompt)

    def test_includes_length_instruction(self):
        etab = EtablissementFactory(ai_response_length="short")
        prompt = _build_system_prompt(etab)
        self.assertIn("1 a 2 phrases", prompt)

    def test_includes_language_instruction(self):
        etab = EtablissementFactory(ai_response_language="en")
        prompt = _build_system_prompt(etab)
        self.assertIn("anglais", prompt)

    def test_includes_etablissement_title(self):
        etab = EtablissementFactory(title="Chez Marcel")
        prompt = _build_system_prompt(etab)
        self.assertIn("Chez Marcel", prompt)

    def test_defaults_for_unknown_tone(self):
        etab = EtablissementFactory(ai_response_tone="unknown")
        prompt = _build_system_prompt(etab)
        self.assertIn("professionnelles", prompt)

    def test_defaults_for_unknown_length(self):
        etab = EtablissementFactory(ai_response_length="unknown")
        prompt = _build_system_prompt(etab)
        self.assertIn("2 a 4 phrases", prompt)

    def test_defaults_for_unknown_language(self):
        etab = EtablissementFactory(ai_response_language="unknown")
        prompt = _build_system_prompt(etab)
        self.assertIn("en francais", prompt)


class TestBuildUserPrompt(TestCase):
    def test_includes_reviewer_name(self):
        review = MagicMock(
            rating=5,
            comment="Super!",
            google_reviewer_data={"displayName": "Jean Dupont"},
        )
        prompt = _build_user_prompt(review, "context")
        self.assertIn("Jean Dupont", prompt)

    def test_uses_default_name_when_no_reviewer_data(self):
        review = MagicMock(rating=3, comment="OK", google_reviewer_data=None)
        prompt = _build_user_prompt(review, "context")
        self.assertIn("Un client", prompt)

    def test_uses_default_name_when_no_display_name(self):
        review = MagicMock(rating=3, comment="OK", google_reviewer_data={})
        prompt = _build_user_prompt(review, "context")
        self.assertIn("Un client", prompt)

    def test_includes_rating(self):
        review = MagicMock(rating=4, comment="Bien", google_reviewer_data=None)
        prompt = _build_user_prompt(review, "context")
        self.assertIn("4/5", prompt)

    def test_handles_no_comment(self):
        review = MagicMock(rating=5, comment=None, google_reviewer_data=None)
        prompt = _build_user_prompt(review, "context")
        self.assertIn("(pas de commentaire)", prompt)

    def test_includes_rating_context(self):
        review = MagicMock(rating=1, comment="Nul", google_reviewer_data=None)
        prompt = _build_user_prompt(review, "Mon contexte spécial")
        self.assertIn("Mon contexte spécial", prompt)


class TestGetUnrepliedReviews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory()

    def test_returns_recent_reviews_when_enough(self):
        now = timezone.now()
        for i in range(5):
            ReviewFactory(
                etablissement=self.etab,
                source="google",
                reply_comment=None,
                ai_response_status=None,
                comment=f"Review {i}",
                writen_at=now - timedelta(hours=i),
            )

        reviews = _get_unreplied_reviews(self.etab)
        self.assertEqual(reviews.count(), 5)

    def test_falls_back_to_min_reviews(self):
        now = timezone.now()
        # Only 1 recent review
        ReviewFactory(
            etablissement=self.etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="Recent",
            writen_at=now - timedelta(hours=1),
        )
        # 2 older reviews
        for i in range(2):
            ReviewFactory(
                etablissement=self.etab,
                source="google",
                reply_comment=None,
                ai_response_status=None,
                comment=f"Old {i}",
                writen_at=now - timedelta(days=5 + i),
            )

        reviews = _get_unreplied_reviews(self.etab)
        self.assertEqual(len(reviews), 3)

    def test_excludes_already_replied_reviews(self):
        now = timezone.now()
        ReviewFactory(
            etablissement=self.etab,
            source="google",
            reply_comment="Already replied",
            ai_response_status=None,
            comment="Review with reply",
            writen_at=now,
        )
        reviews = _get_unreplied_reviews(self.etab)
        self.assertEqual(reviews.count(), 0)

    def test_excludes_reviews_with_ai_status(self):
        now = timezone.now()
        ReviewFactory(
            etablissement=self.etab,
            source="google",
            reply_comment=None,
            ai_response_status="pending",
            comment="Pending AI",
            writen_at=now,
        )
        reviews = _get_unreplied_reviews(self.etab)
        self.assertEqual(reviews.count(), 0)

    def test_excludes_empty_comments(self):
        now = timezone.now()
        ReviewFactory(
            etablissement=self.etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="",
            writen_at=now,
        )
        reviews = _get_unreplied_reviews(self.etab)
        self.assertEqual(reviews.count(), 0)


class TestCheckMalicious(TestCase):
    def test_flags_short_comment(self):
        review = MagicMock(comment="Nul", rating=1, etablissement_id=1, id=1)
        is_flagged, reason = _check_malicious(review)
        self.assertTrue(is_flagged)
        self.assertIn("commentaire très court", reason)

    def test_flags_no_comment(self):
        review = MagicMock(comment=None, rating=1, etablissement_id=1, id=1)
        is_flagged, _reason = _check_malicious(review)
        self.assertTrue(is_flagged)

    def test_flags_empty_comment(self):
        review = MagicMock(comment="", rating=1, etablissement_id=1, id=1)
        is_flagged, _reason = _check_malicious(review)
        self.assertTrue(is_flagged)

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_flags_ai_detected_malicious(self, mock_generate):
        mock_generate.return_value = "OUI - suspect"
        review = MagicMock(
            comment="Ce restaurant est horrible et je déteste tout",
            rating=1,
            etablissement_id=1,
            id=1,
        )
        is_flagged, reason = _check_malicious(review)
        self.assertTrue(is_flagged)
        self.assertIn("malveillant", reason)

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_not_flagged_when_ai_says_no(self, mock_generate):
        mock_generate.return_value = "NON - légitime"
        review = MagicMock(
            comment="Le service était décevant, attente de 45 minutes pour le plat principal",
            rating=1,
            etablissement_id=1,
            id=1,
        )
        is_flagged, reason = _check_malicious(review)
        self.assertFalse(is_flagged)
        self.assertEqual(reason, "")

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_not_flagged_on_api_error(self, mock_generate):
        mock_generate.side_effect = Exception("API error")
        review = MagicMock(
            comment="Le service était décevant, attente de 45 minutes",
            rating=1,
            etablissement_id=1,
            id=1,
        )
        is_flagged, _reason = _check_malicious(review)
        self.assertFalse(is_flagged)


class TestGenerateAndSendResponses(TestCase):
    def test_returns_early_when_ai_not_enabled(self):
        etab = EtablissementFactory(ai_responses_enabled=False)
        result = generate_and_send_responses(etab)
        self.assertEqual(result["total_reviews"], 0)
        self.assertIn("AI responses not enabled", result["errors"])

    def test_returns_early_when_no_unreplied_reviews(self):
        etab = EtablissementFactory(ai_responses_enabled=True)
        result = generate_and_send_responses(etab)
        self.assertEqual(result["total_reviews"], 0)
        self.assertEqual(result["responded"], 0)

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_validation_mode_saves_as_pending(self, mock_generate):
        mock_generate.return_value = "Merci pour votre avis!"
        etab = EtablissementFactory(
            ai_responses_enabled=True,
            ai_response_validation_required=True,
            ai_response_malicious_protection=False,
        )
        ReviewFactory(
            etablissement=etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="Excellent restaurant!",
            rating=5,
            writen_at=timezone.now(),
            google_review_id="review_1",
        )

        result = generate_and_send_responses(etab)

        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["responded"], 0)

    @patch("apps.tasks_api.services.ai_response_service._post_reply_to_google")
    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_auto_post_mode_posts_to_google(self, mock_generate, mock_post):
        mock_generate.return_value = "Merci beaucoup!"
        etab = EtablissementFactory(
            ai_responses_enabled=True,
            ai_response_validation_required=False,
            ai_response_malicious_protection=False,
        )
        ReviewFactory(
            etablissement=etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="Très bon accueil",
            rating=5,
            writen_at=timezone.now(),
            google_review_id="review_2",
        )

        with patch.object(etab.google_credential, "get_reviews_service", return_value=MagicMock()):
            result = generate_and_send_responses(etab)

        self.assertEqual(result["responded"], 1)
        mock_post.assert_called_once()

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_flagged_reviews_saved_as_flagged(self, mock_generate):
        mock_generate.return_value = "Réponse IA"
        etab = EtablissementFactory(
            ai_responses_enabled=True,
            ai_response_validation_required=True,
            ai_response_malicious_protection=True,
        )
        ReviewFactory(
            etablissement=etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="Nul",  # Short comment triggers heuristic flag
            rating=1,
            writen_at=timezone.now(),
            google_review_id="review_3",
        )

        result = generate_and_send_responses(etab)

        self.assertEqual(result["flagged"], 1)

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_returns_error_when_reviews_service_is_none(self, mock_generate):
        mock_generate.return_value = "Merci!"
        etab = EtablissementFactory(
            ai_responses_enabled=True,
            ai_response_validation_required=False,
            ai_response_malicious_protection=False,
        )
        ReviewFactory(
            etablissement=etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="Great place!",
            rating=5,
            writen_at=timezone.now(),
            google_review_id="review_4",
        )

        with patch.object(etab.google_credential, "get_reviews_service", return_value=None):
            result = generate_and_send_responses(etab)

        self.assertIn("Unable to initialize", result["errors"][0])
        self.assertEqual(result["failed"], result["total_reviews"])

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_handles_generate_response_failure(self, mock_generate):
        mock_generate.side_effect = Exception("OpenRouter is down")
        etab = EtablissementFactory(
            ai_responses_enabled=True,
            ai_response_validation_required=True,
            ai_response_malicious_protection=False,
        )
        ReviewFactory(
            etablissement=etab,
            source="google",
            reply_comment=None,
            ai_response_status=None,
            comment="Un bon endroit pour manger",
            rating=4,
            writen_at=timezone.now(),
            google_review_id="review_5",
        )

        result = generate_and_send_responses(etab)

        self.assertEqual(result["failed"], 1)
        self.assertTrue(len(result["errors"]) > 0)


class TestApproveAiResponse(TestCase):
    @patch("apps.tasks_api.services.ai_response_service._post_reply_to_google")
    @patch("apps.private.auths.models.GoogleCredentials.get_reviews_service")
    def test_approves_and_posts(self, mock_get_service, mock_post):
        mock_get_service.return_value = MagicMock()
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment="Brouillon IA",
            ai_response_status="pending",
            google_review_id="review_approve",
        )

        result = approve_ai_response(review.id)

        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch("apps.tasks_api.services.ai_response_service._post_reply_to_google")
    @patch("apps.private.auths.models.GoogleCredentials.get_reviews_service")
    def test_approves_with_edited_comment(self, mock_get_service, mock_post):
        mock_get_service.return_value = MagicMock()
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment="Original draft",
            ai_response_status="pending",
            google_review_id="review_edit",
        )

        result = approve_ai_response(review.id, edited_comment="Commentaire modifié")

        self.assertTrue(result)
        mock_post.assert_called_once()
        args = mock_post.call_args
        self.assertEqual(args[0][1], "Commentaire modifié")

    def test_returns_false_when_no_draft(self):
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment=None,
            ai_response_status="pending",
            google_review_id="review_nodraft",
        )
        result = approve_ai_response(review.id)
        self.assertFalse(result)

    @patch("apps.private.auths.models.GoogleCredentials.get_reviews_service")
    def test_returns_false_when_no_reviews_service(self, mock_get_service):
        mock_get_service.return_value = None
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment="Draft",
            ai_response_status="pending",
            google_review_id="review_noservice",
        )

        result = approve_ai_response(review.id)

        self.assertFalse(result)


class TestRejectAiResponse(TestCase):
    def test_rejects_review(self):
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment="Draft to reject",
            ai_response_status="pending",
            ai_flag_reason="Some reason",
        )

        result = reject_ai_response(review.id)

        self.assertTrue(result)
        review.refresh_from_db()
        self.assertEqual(review.ai_response_status, "rejected")
        self.assertIsNone(review.ai_draft_comment)
        self.assertIsNone(review.ai_flag_reason)

    def test_returns_false_on_invalid_id(self):
        result = reject_ai_response(99999)
        self.assertFalse(result)


class TestRegenerateAiResponse(TestCase):
    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_regenerates_draft(self, mock_generate):
        mock_generate.return_value = "Nouvelle réponse IA"
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment="Ancien brouillon",
            ai_response_status="pending",
            comment="Bon restaurant",
            rating=4,
        )

        result = regenerate_ai_response(review.id)

        self.assertEqual(result, "Nouvelle réponse IA")
        review.refresh_from_db()
        self.assertEqual(review.ai_draft_comment, "Nouvelle réponse IA")
        # Status should remain unchanged
        self.assertEqual(review.ai_response_status, "pending")

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_preserves_flagged_status(self, mock_generate):
        mock_generate.return_value = "Réponse régénérée"
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            ai_draft_comment="Old draft",
            ai_response_status="flagged",
            comment="Review text",
            rating=2,
        )

        regenerate_ai_response(review.id)

        review.refresh_from_db()
        self.assertEqual(review.ai_response_status, "flagged")

    @patch("apps.tasks_api.services.ai_response_service.generate_response")
    def test_returns_none_on_error(self, mock_generate):
        mock_generate.side_effect = Exception("API error")
        etab = EtablissementFactory()
        review = ReviewFactory(
            etablissement=etab,
            source="google",
            comment="Review",
            rating=3,
        )

        result = regenerate_ai_response(review.id)

        self.assertIsNone(result)

    def test_returns_none_on_invalid_id(self):
        result = regenerate_ai_response(99999)
        self.assertIsNone(result)
