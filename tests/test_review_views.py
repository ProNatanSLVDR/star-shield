from django.test import Client, TestCase
from django.urls import reverse

from apps.public.reviews.models import Review, ReviewAnalytics
from tests.factories import EtablissementFactory


class TestFeedbackView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(
            active=True,
            review_filtering_enabled=True,
        )

    def test_renders_page(self):
        response = self.client.get(reverse("reviews:feedback", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 200)

    def test_creates_analytics_on_first_visit(self):
        self.client.get(reverse("reviews:feedback", args=[self.etab.slug]))

        self.assertEqual(
            ReviewAnalytics.objects.filter(etablissement=self.etab, type="feedback_viewed").count(),
            1,
        )

    def test_redirects_when_inactive(self):
        self.etab.active = False
        self.etab.save(update_fields=["active"])

        response = self.client.get(reverse("reviews:feedback", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)

    def test_redirects_when_filtering_disabled(self):
        self.etab.review_filtering_enabled = False
        self.etab.save(update_fields=["review_filtering_enabled"])

        response = self.client.get(reverse("reviews:feedback", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)


class TestInternalFeedbackView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True)

    def test_get_renders_form(self):
        response = self.client.get(reverse("reviews:internal_feedback", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 200)

    def test_post_creates_review(self):
        response = self.client.post(
            reverse("reviews:internal_feedback", args=[self.etab.slug]),
            data={"rating": 3, "comment": "Could be better"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Review.objects.filter(etablissement=self.etab, source="internal").count(),
            1,
        )

    def test_post_invalid_shows_form(self):
        response = self.client.post(
            reverse("reviews:internal_feedback", args=[self.etab.slug]),
            data={"comment": "No rating"},
        )

        # Should re-render the form (not redirect)
        self.assertEqual(response.status_code, 200)

    def test_creates_analytics_on_visit(self):
        self.client.get(reverse("reviews:internal_feedback", args=[self.etab.slug]))

        self.assertEqual(
            ReviewAnalytics.objects.filter(etablissement=self.etab, type="feedback_internal_viewed").count(),
            1,
        )


class TestExternalFeedbackView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(
            active=True,
            new_reviews_uri="https://search.google.com/local/writereview?placeid=test",
        )

    def test_redirects_to_google(self):
        response = self.client.get(reverse("reviews:external_feedback", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("google.com", response.url)

    def test_creates_analytics(self):
        self.client.get(reverse("reviews:external_feedback", args=[self.etab.slug]))

        self.assertEqual(
            ReviewAnalytics.objects.filter(etablissement=self.etab, type="feedback_external").count(),
            1,
        )
