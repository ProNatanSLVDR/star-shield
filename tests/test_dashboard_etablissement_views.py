from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tests.factories import (
    EtablissementFactory,
    RatingHistoryFactory,
    ReviewAnalyticsFactory,
    ReviewFactory,
)


class DashboardEtablissementMixin:
    """Shared setUp for single-etablissement views."""

    def setUp(self):
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()


class TestOverviewView(DashboardEtablissementMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("etablissement", response.context)
        self.assertIn("general_stats", response.context)

    def test_with_reviews(self):
        ReviewFactory(etablissement=self.etab, rating=5, source="google")
        ReviewFactory(etablissement=self.etab, rating=3, source="internal")
        RatingHistoryFactory(etablissement=self.etab)
        response = self.client.get(reverse("dashboard:etablissement:overview"))
        self.assertEqual(response.status_code, 200)

    def test_no_selected_etab_redirects(self):
        session = self.client.session
        del session["selected_etablissement"]
        session.save()
        response = self.client.get(reverse("dashboard:etablissement:overview"))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:etablissement:overview"))
        self.assertEqual(response.status_code, 302)


class TestStatsView(DashboardEtablissementMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:stats"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("stats_items", response.context)
        self.assertIn("chart_payload_json", response.context)

    def test_with_review_data(self):
        ReviewFactory(etablissement=self.etab, rating=5, source="google")
        ReviewFactory(etablissement=self.etab, rating=2, source="internal")
        ReviewAnalyticsFactory(etablissement=self.etab, type="feedback_viewed")
        ReviewAnalyticsFactory(etablissement=self.etab, type="feedback_external")
        response = self.client.get(reverse("dashboard:etablissement:stats"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("rating_distribution", response.context)

    def test_empty_data(self):
        response = self.client.get(reverse("dashboard:etablissement:stats"))
        self.assertEqual(response.status_code, 200)


class TestAvisView(DashboardEtablissementMixin, TestCase):
    def _create_reviews(self):
        for rating in [1, 2, 3, 4, 5]:
            ReviewFactory(
                etablissement=self.etab,
                rating=rating,
                source="google" if rating >= 4 else "internal",
            )

    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:avis"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("reviews", response.context)
        self.assertIn("filters", response.context)

    def test_source_filter_google(self):
        self._create_reviews()
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"source": "google"})
        self.assertEqual(response.status_code, 200)

    def test_source_filter_internal(self):
        self._create_reviews()
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"source": "internal"})
        self.assertEqual(response.status_code, 200)

    def test_rating_filter(self):
        self._create_reviews()
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"rating": "5"})
        self.assertEqual(response.status_code, 200)

    def test_invalid_rating_filter_ignored(self):
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"rating": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_date_preset_7days(self):
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"date_preset": "7days"})
        self.assertEqual(response.status_code, 200)

    def test_date_preset_all_time(self):
        self._create_reviews()
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"date_preset": "all_time"})
        self.assertEqual(response.status_code, 200)

    def test_custom_date_range(self):
        today = timezone.now().date()
        response = self.client.get(
            reverse("dashboard:etablissement:avis"),
            {
                "date_from": (today - timedelta(days=60)).strftime("%Y-%m-%d"),
                "date_to": today.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_order_by_rating_asc(self):
        self._create_reviews()
        response = self.client.get(
            reverse("dashboard:etablissement:avis"),
            {"order_by": "rating", "order_dir": "asc", "date_preset": "all_time"},
        )
        self.assertEqual(response.status_code, 200)

    def test_order_by_rating_desc(self):
        self._create_reviews()
        response = self.client.get(
            reverse("dashboard:etablissement:avis"),
            {"order_by": "rating", "order_dir": "desc", "date_preset": "all_time"},
        )
        self.assertEqual(response.status_code, 200)

    def test_order_by_date_asc(self):
        response = self.client.get(
            reverse("dashboard:etablissement:avis"),
            {"order_by": "date", "order_dir": "asc"},
        )
        self.assertEqual(response.status_code, 200)

    def test_pagination(self):
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"page": "1"})
        self.assertEqual(response.status_code, 200)

    def test_invalid_page_defaults_to_1(self):
        response = self.client.get(reverse("dashboard:etablissement:avis"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_default_filters(self):
        response = self.client.get(reverse("dashboard:etablissement:avis"))
        filters = response.context["filters"]
        self.assertEqual(filters["source"], "all")
        self.assertEqual(filters["rating"], "all")
        self.assertEqual(filters["date_preset"], "30days")
        self.assertEqual(filters["order_by"], "date")
        self.assertEqual(filters["order_dir"], "desc")


class TestRefreshReviewsView(DashboardEtablissementMixin, TestCase):
    @patch("apps.private.dashboard.views.etablissement.views.enqueue_refresh_task")
    def test_refresh_success(self, mock_enqueue):
        self.etab.last_reviews_update = None
        self.etab.save()
        response = self.client.post(reverse("dashboard:etablissement:refresh"))
        self.assertEqual(response.status_code, 302)
        mock_enqueue.assert_called_once_with(self.etab.id)

    @patch("apps.private.dashboard.views.etablissement.views.enqueue_refresh_task")
    def test_refresh_rate_limited(self, mock_enqueue):
        self.etab.last_reviews_update = timezone.now() - timedelta(minutes=5)
        self.etab.save()
        response = self.client.post(reverse("dashboard:etablissement:refresh"))
        self.assertEqual(response.status_code, 302)
        mock_enqueue.assert_not_called()

    @patch("apps.private.dashboard.views.etablissement.views.enqueue_refresh_task")
    def test_refresh_after_cooldown(self, mock_enqueue):
        self.etab.last_reviews_update = timezone.now() - timedelta(minutes=35)
        self.etab.save()
        response = self.client.post(reverse("dashboard:etablissement:refresh"))
        self.assertEqual(response.status_code, 302)
        mock_enqueue.assert_called_once()

    def test_refresh_requires_post(self):
        response = self.client.get(reverse("dashboard:etablissement:refresh"))
        self.assertEqual(response.status_code, 405)

    @patch("apps.private.dashboard.views.etablissement.views.enqueue_refresh_task")
    def test_refresh_error_handling(self, mock_enqueue):
        mock_enqueue.side_effect = Exception("Queue error")
        self.etab.last_reviews_update = None
        self.etab.save()
        response = self.client.post(reverse("dashboard:etablissement:refresh"))
        self.assertEqual(response.status_code, 302)
