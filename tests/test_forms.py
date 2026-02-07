from django.test import SimpleTestCase

from apps.public.reviews.forms import FeedbackForm
from apps.public.roulette.forms import RedeemPrizeCodeForm


class TestFeedbackForm(SimpleTestCase):
    def test_valid_data(self):
        form = FeedbackForm(data={"rating": 4, "comment": "Great!"})

        self.assertTrue(form.is_valid())

    def test_rating_required(self):
        form = FeedbackForm(data={"comment": "No rating"})

        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_rating_min_value(self):
        form = FeedbackForm(data={"rating": 0})

        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_rating_max_value(self):
        form = FeedbackForm(data={"rating": 6})

        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_comment_optional(self):
        form = FeedbackForm(data={"rating": 3})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["comment"], "")

    def test_comment_stripped(self):
        form = FeedbackForm(data={"rating": 3, "comment": "  Hello  "})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["comment"], "Hello")


class TestRedeemPrizeCodeForm(SimpleTestCase):
    def test_valid_code(self):
        form = RedeemPrizeCodeForm(data={"code": "ABC123"})

        self.assertTrue(form.is_valid())

    def test_code_required(self):
        form = RedeemPrizeCodeForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)
