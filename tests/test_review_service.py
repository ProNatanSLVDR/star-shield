from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.private.auths.models import RatingHistory
from apps.public.reviews.models import Review
from apps.tasks_api.services.review_service import fetch_reviews, fetch_stats
from tests.factories import EtablissementFactory


class TestFetchStats(TestCase):
    def test_creates_rating_history_record(self):
        etab = EtablissementFactory()

        # Mock the reviews service
        mock_service = MagicMock()
        mock_service.accounts().locations().reviews().list().execute.return_value = {
            "averageRating": 4.2,
            "totalReviewCount": 50,
        }

        with patch.object(etab.google_credential, "get_reviews_service", return_value=mock_service):
            fetch_stats(etab)

        history = RatingHistory.objects.filter(etablissement=etab).first()
        self.assertIsNotNone(history)
        self.assertEqual(float(history.rating), 4.2)
        self.assertEqual(history.total_reviews, 50)

    def test_raises_when_service_unavailable(self):
        etab = EtablissementFactory()

        with (
            patch.object(etab.google_credential, "get_reviews_service", return_value=None),
            self.assertRaises(RuntimeError),
        ):
            fetch_stats(etab)

    def test_raises_on_api_error(self):
        etab = EtablissementFactory()

        mock_service = MagicMock()
        mock_service.accounts().locations().reviews().list().execute.side_effect = Exception("API Error")

        with (
            patch.object(etab.google_credential, "get_reviews_service", return_value=mock_service),
            self.assertRaises(RuntimeError),
        ):
            fetch_stats(etab)

    def test_handles_missing_data(self):
        etab = EtablissementFactory()

        mock_service = MagicMock()
        mock_service.accounts().locations().reviews().list().execute.return_value = {}

        with patch.object(etab.google_credential, "get_reviews_service", return_value=mock_service):
            fetch_stats(etab)

        history = RatingHistory.objects.filter(etablissement=etab).first()
        self.assertEqual(float(history.rating), 0)
        self.assertEqual(history.total_reviews, 0)


class TestFetchReviews(TestCase):
    def test_creates_new_review_records(self):
        etab = EtablissementFactory()

        mock_service = MagicMock()
        mock_service.accounts().locations().reviews().list().execute.return_value = {
            "reviews": [
                {
                    "reviewId": "rev_1",
                    "starRating": "FIVE",
                    "comment": "Amazing!",
                    "reviewer": {"displayName": "Alice"},
                    "createTime": "2024-01-01T00:00:00Z",
                },
                {
                    "reviewId": "rev_2",
                    "starRating": "THREE",
                    "comment": "OK",
                    "reviewer": {"displayName": "Bob"},
                    "createTime": "2024-01-02T00:00:00Z",
                },
            ],
        }

        with patch.object(etab.google_credential, "get_reviews_service", return_value=mock_service):
            fetch_reviews(etab)

        self.assertEqual(Review.objects.filter(etablissement=etab, source="google").count(), 2)

    def test_deduplicates_existing_reviews(self):
        etab = EtablissementFactory()
        Review.objects.create(
            etablissement=etab,
            source="google",
            google_review_id="rev_existing",
            rating=4,
        )

        mock_service = MagicMock()
        mock_service.accounts().locations().reviews().list().execute.return_value = {
            "reviews": [
                {
                    "reviewId": "rev_existing",
                    "starRating": "FOUR",
                    "comment": "Updated comment",
                    "reviewer": {"displayName": "Alice"},
                    "createTime": "2024-01-01T00:00:00Z",
                },
            ],
        }

        with patch.object(etab.google_credential, "get_reviews_service", return_value=mock_service):
            fetch_reviews(etab)

        # Should still be 1 review, not 2
        reviews = Review.objects.filter(etablissement=etab, source="google")
        self.assertEqual(reviews.count(), 1)
        self.assertEqual(reviews.first().comment, "Updated comment")

    def test_raises_when_service_unavailable(self):
        etab = EtablissementFactory()

        with (
            patch.object(etab.google_credential, "get_reviews_service", return_value=None),
            self.assertRaises(RuntimeError),
        ):
            fetch_reviews(etab)

    def test_handles_review_with_reply(self):
        etab = EtablissementFactory()

        mock_service = MagicMock()
        mock_service.accounts().locations().reviews().list().execute.return_value = {
            "reviews": [
                {
                    "reviewId": "rev_with_reply",
                    "starRating": "FIVE",
                    "comment": "Great!",
                    "reviewer": {"displayName": "Charlie"},
                    "createTime": "2024-01-01T00:00:00Z",
                    "reviewReply": {
                        "comment": "Thank you!",
                        "updateTime": "2024-01-02T00:00:00Z",
                    },
                },
            ],
        }

        with patch.object(etab.google_credential, "get_reviews_service", return_value=mock_service):
            fetch_reviews(etab)

        review = Review.objects.get(google_review_id="rev_with_reply")
        self.assertEqual(review.reply_comment, "Thank you!")
        self.assertEqual(review.reply_type, "google")
