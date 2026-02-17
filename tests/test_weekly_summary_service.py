from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.private.auths.models import WeeklyPerformanceSummary
from apps.tasks_api.services.weekly_summary_service import (
    collect_weekly_metrics,
    generate_and_store_weekly_summary,
    generate_weekly_summary,
    get_previous_week_start,
    get_week_start_date,
    parse_summary_sections,
)
from tests.factories import (
    EtablissementFactory,
    RatingHistoryFactory,
    ReviewAnalyticsFactory,
    ReviewFactory,
)


class TestGetWeekStartDate(TestCase):
    def test_returns_monday_for_wednesday(self):
        # 2026-02-18 is a Wednesday
        result = get_week_start_date(date(2026, 2, 18))
        self.assertEqual(result, date(2026, 2, 16))  # Monday

    def test_returns_same_date_for_monday(self):
        result = get_week_start_date(date(2026, 2, 16))
        self.assertEqual(result, date(2026, 2, 16))

    def test_returns_monday_for_sunday(self):
        result = get_week_start_date(date(2026, 2, 22))
        self.assertEqual(result, date(2026, 2, 16))

    def test_returns_monday_for_saturday(self):
        result = get_week_start_date(date(2026, 2, 21))
        self.assertEqual(result, date(2026, 2, 16))

    def test_handles_none_uses_current_date(self):
        result = get_week_start_date(None)
        # Should be a Monday (weekday 0)
        self.assertEqual(result.weekday(), 0)


class TestGetPreviousWeekStart(TestCase):
    def test_returns_previous_monday(self):
        result = get_previous_week_start(date(2026, 2, 16))
        self.assertEqual(result, date(2026, 2, 9))

    def test_returns_7_days_before(self):
        monday = date(2026, 1, 5)
        result = get_previous_week_start(monday)
        self.assertEqual(result, date(2025, 12, 29))


class TestCollectWeeklyMetrics(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory()
        cls.week_start = date(2026, 2, 9)  # Monday
        week_start_dt = timezone.make_aware(datetime.combine(cls.week_start, datetime.min.time()))
        week_end_dt = timezone.make_aware(datetime.combine(cls.week_start + timedelta(days=6), datetime.max.time()))

        # Create reviews during the week
        for i in range(3):
            ReviewFactory(
                etablissement=cls.etab,
                source="google",
                rating=4 + (i % 2),
                writen_at=week_start_dt + timedelta(days=i),
                comment=f"Review {i}",
                google_reviewer_data={"displayName": f"User {i}"},
            )

        # Create rating history - use .update() to set auto_now_add field
        from apps.private.auths.models import RatingHistory

        rh1 = RatingHistoryFactory(etablissement=cls.etab, rating=4.2)
        RatingHistory.objects.filter(pk=rh1.pk).update(created_at=week_start_dt - timedelta(hours=1))

        rh2 = RatingHistoryFactory(etablissement=cls.etab, rating=4.5)
        RatingHistory.objects.filter(pk=rh2.pk).update(created_at=week_end_dt - timedelta(hours=1))

        # Create analytics - use .update() to set auto_now_add field
        from apps.public.reviews.models import ReviewAnalytics

        a1 = ReviewAnalyticsFactory(etablissement=cls.etab, type="feedback_viewed")
        ReviewAnalytics.objects.filter(pk=a1.pk).update(created_at=week_start_dt + timedelta(days=1))

        a2 = ReviewAnalyticsFactory(etablissement=cls.etab, type="feedback_external")
        ReviewAnalytics.objects.filter(pk=a2.pk).update(created_at=week_start_dt + timedelta(days=2))

    def test_collects_review_counts(self):
        metrics = collect_weekly_metrics(self.etab, self.week_start)
        self.assertEqual(metrics["new_reviews_count"], 3)

    def test_collects_rating_changes(self):
        metrics = collect_weekly_metrics(self.etab, self.week_start)
        self.assertAlmostEqual(metrics["rating_at_start"], 4.2, places=1)
        self.assertAlmostEqual(metrics["rating_at_end"], 4.5, places=1)

    def test_collects_analytics_counts(self):
        metrics = collect_weekly_metrics(self.etab, self.week_start)
        self.assertEqual(metrics["qr_page_visits"], 1)
        self.assertEqual(metrics["reviews_redirected_google"], 1)

    def test_includes_review_texts(self):
        metrics = collect_weekly_metrics(self.etab, self.week_start)
        self.assertTrue(len(metrics["review_texts"]) > 0)
        self.assertIn("rating", metrics["review_texts"][0])
        self.assertIn("comment", metrics["review_texts"][0])

    def test_includes_previous_week_comparison(self):
        metrics = collect_weekly_metrics(self.etab, self.week_start)
        self.assertIn("previous_week", metrics)
        self.assertIn("new_reviews_count", metrics["previous_week"])

    def test_handles_empty_data(self):
        etab = EtablissementFactory()
        metrics = collect_weekly_metrics(etab, self.week_start)
        self.assertEqual(metrics["new_reviews_count"], 0)
        self.assertIsNone(metrics["rating_at_start"])
        self.assertIsNone(metrics["rating_at_end"])


class TestParseSummarySections(TestCase):
    def test_parses_three_sections(self):
        raw = (
            "---SHORT_SUMMARY---\n"
            "Bonne semaine!\n"
            "---FULL_REPORT---\n"
            "Le rapport complet.\n"
            "---ADVICE---\n"
            "Continuez comme ça!"
        )
        result = parse_summary_sections(raw)
        self.assertEqual(result["short_summary"], "Bonne semaine!")
        self.assertEqual(result["summary_text"], "Le rapport complet.")
        self.assertEqual(result["advice_text"], "Continuez comme ça!")

    def test_fallback_when_markers_missing(self):
        raw = "Just some plain text summary without any markers."
        result = parse_summary_sections(raw)
        self.assertEqual(result["summary_text"], raw.strip())
        self.assertEqual(result["short_summary"], raw.strip())
        self.assertEqual(result["advice_text"], "")

    def test_fallback_truncates_long_short_summary(self):
        raw = "A" * 300
        result = parse_summary_sections(raw)
        self.assertTrue(result["short_summary"].endswith("..."))
        self.assertEqual(len(result["short_summary"]), 203)  # 200 + "..."

    def test_handles_empty_sections(self):
        raw = "---SHORT_SUMMARY---\n---FULL_REPORT---\n---ADVICE---\n"
        result = parse_summary_sections(raw)
        self.assertEqual(result["short_summary"], "")
        self.assertEqual(result["summary_text"], "")
        self.assertEqual(result["advice_text"], "")


class TestGenerateWeeklySummary(TestCase):
    @patch("apps.tasks_api.services.weekly_summary_service.generate_response")
    def test_calls_generate_response(self, mock_generate):
        mock_generate.return_value = "---SHORT_SUMMARY---\nBref\n---FULL_REPORT---\nRapport\n---ADVICE---\nConseil"
        etab = EtablissementFactory()
        metrics = {
            "week_start_date": "2026-02-09",
            "week_end_date": "2026-02-15",
            "new_reviews_count": 5,
            "rating_at_start": 4.0,
            "rating_at_end": 4.2,
            "total_reviews_at_end": 100,
            "qr_page_visits": 50,
            "reviews_redirected_google": 30,
            "reviews_kept_private": 10,
            "internal_feedback_submitted": 5,
            "ai_responses_count": 3,
            "review_texts": [],
            "previous_week": {
                "new_reviews_count": 3,
                "qr_page_visits": 40,
                "reviews_redirected_google": 25,
            },
        }

        result = generate_weekly_summary(etab, metrics)

        mock_generate.assert_called_once()
        self.assertEqual(result["short_summary"], "Bref")
        self.assertEqual(result["summary_text"], "Rapport")
        self.assertEqual(result["advice_text"], "Conseil")

    @patch("apps.tasks_api.services.weekly_summary_service.generate_response")
    def test_raises_on_error(self, mock_generate):
        mock_generate.side_effect = Exception("API Error")
        etab = EtablissementFactory()

        with self.assertRaises(Exception):  # noqa: B017
            generate_weekly_summary(etab, {})


class TestGenerateAndStoreWeeklySummary(TestCase):
    @patch("apps.tasks_api.services.weekly_summary_service.generate_response")
    def test_creates_summary(self, mock_generate):
        mock_generate.return_value = "---SHORT_SUMMARY---\nBref\n---FULL_REPORT---\nRapport\n---ADVICE---\nConseil"
        etab = EtablissementFactory()
        week_start = date(2026, 2, 9)

        summary = generate_and_store_weekly_summary(etab, week_start)

        self.assertIsInstance(summary, WeeklyPerformanceSummary)
        self.assertEqual(summary.etablissement, etab)
        self.assertEqual(summary.week_start_date, week_start)
        self.assertEqual(summary.short_summary, "Bref")

    @patch("apps.tasks_api.services.weekly_summary_service.generate_response")
    def test_returns_existing_if_duplicate(self, mock_generate):
        etab = EtablissementFactory()
        week_start = date(2026, 2, 9)

        existing = WeeklyPerformanceSummary.objects.create(
            etablissement=etab,
            week_start_date=week_start,
            short_summary="Existing",
            summary_text="Already exists",
        )

        result = generate_and_store_weekly_summary(etab, week_start)

        self.assertEqual(result.id, existing.id)
        mock_generate.assert_not_called()

    @patch("apps.tasks_api.services.weekly_summary_service.generate_response")
    def test_defaults_to_previous_week(self, mock_generate):
        mock_generate.return_value = "---SHORT_SUMMARY---\nBref\n---FULL_REPORT---\nRapport\n---ADVICE---\nConseil"
        etab = EtablissementFactory()

        summary = generate_and_store_weekly_summary(etab)

        # Should have created summary for previous week (a Monday)
        self.assertEqual(summary.week_start_date.weekday(), 0)
        self.assertTrue(summary.week_start_date < timezone.now().date())
