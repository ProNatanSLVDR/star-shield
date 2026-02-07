from django.http import Http404
from django.test import SimpleTestCase, TestCase

from apps.public.reviews.utils import (
    build_feedback_context,
    calcul_objectif,
    estimations,
    get_etablissement_by_identifier,
    google_stars_to_number,
)
from tests.factories import EtablissementFactory


class TestGoogleStarsToNumber(SimpleTestCase):
    def test_all_star_values(self):
        cases = [
            ("ONE", 1),
            ("TWO", 2),
            ("THREE", 3),
            ("FOUR", 4),
            ("FIVE", 5),
        ]
        for star_str, expected in cases:
            with self.subTest(star_str=star_str):
                self.assertEqual(google_stars_to_number(star_str), expected)

    def test_unknown_value_returns_zero(self):
        self.assertEqual(google_stars_to_number("UNKNOWN"), 0)

    def test_empty_string_returns_zero(self):
        self.assertEqual(google_stars_to_number(""), 0)

    def test_none_returns_zero(self):
        self.assertEqual(google_stars_to_number(None), 0)


class TestCalculObjectif(SimpleTestCase):
    def test_returns_dict_with_expected_keys(self):
        result = calcul_objectif(noteactu=3.5, nb_notes=10, objectif=4.0)

        self.assertIsInstance(result, dict)
        for key in ["1_stars_needed", "2_stars_needed", "3_stars_needed", "4_stars_needed", "5_stars_needed"]:
            self.assertIn(key, result)

    def test_low_rating_needs_more_5_stars(self):
        result = calcul_objectif(noteactu=2.0, nb_notes=10, objectif=4.5)

        self.assertIsNotNone(result["5_stars_needed"])
        self.assertGreater(result["5_stars_needed"], 0)

    def test_high_rating_needs_fewer_stars(self):
        result = calcul_objectif(noteactu=4.4, nb_notes=10, objectif=4.5)

        self.assertIsNotNone(result["5_stars_needed"])
        self.assertGreater(result["5_stars_needed"], 0)

    def test_already_met_goal_needs_zero(self):
        result = calcul_objectif(noteactu=4.8, nb_notes=100, objectif=4.5)

        self.assertEqual(result["5_stars_needed"], 0)

    def test_unreachable_with_lower_stars_returns_none(self):
        # Stars below objective can't raise the average
        result = calcul_objectif(noteactu=3.0, nb_notes=10, objectif=4.5)

        # Stars 1-4 are all below 4.5, so they should be None
        self.assertIsNone(result["1_stars_needed"])
        self.assertIsNone(result["2_stars_needed"])
        self.assertIsNone(result["3_stars_needed"])
        self.assertIsNone(result["4_stars_needed"])


class TestEstimations(SimpleTestCase):
    def test_returns_dict_with_threshold_keys(self):
        result = estimations(note_actuelle=3.5, nb_notes=50, objectif=4.0, notes_par_semaine=5)

        self.assertIsInstance(result, dict)
        self.assertIn("at_threshold_3", result)
        self.assertIn("at_threshold_4", result)
        self.assertIn("at_threshold_5", result)

    def test_reachable_goal_returns_weeks(self):
        result = estimations(note_actuelle=3.0, nb_notes=100, objectif=4.5, notes_par_semaine=5)

        # With threshold 5 (only 5-star reviews), should be reachable but take multiple weeks
        self.assertIsNotNone(result["at_threshold_5"])
        self.assertGreaterEqual(result["at_threshold_5"], 0)

    def test_already_met_goal_returns_zero(self):
        result = estimations(note_actuelle=4.8, nb_notes=100, objectif=4.5, notes_par_semaine=5)

        # All thresholds should return 0 (already at goal)
        self.assertEqual(result["at_threshold_5"], 0)


class TestGetEtablissementByIdentifier(TestCase):
    def test_finds_by_slug(self):
        etab = EtablissementFactory(slug="my-restaurant")

        result = get_etablissement_by_identifier("my-restaurant")

        self.assertEqual(result, etab)

    def test_finds_by_uuid(self):
        etab = EtablissementFactory()

        result = get_etablissement_by_identifier(str(etab.uuid))

        self.assertEqual(result, etab)

    def test_raises_404_for_missing(self):
        with self.assertRaises(Http404):
            get_etablissement_by_identifier("nonexistent-slug")

    def test_raises_404_for_empty(self):
        with self.assertRaises(Http404):
            get_etablissement_by_identifier("")

    def test_raises_404_for_invalid_uuid(self):
        with self.assertRaises(Http404):
            get_etablissement_by_identifier("not-a-valid-uuid-or-slug-that-exists")


class TestBuildFeedbackContext(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory(
            review_threshold=4,
            review_accent_color="#ff0000",
            review_show_etablissement_pill=True,
        )

    def test_returns_expected_keys(self):
        ctx = build_feedback_context(self.etab, str(self.etab.slug))

        expected_keys = {
            "etablissement",
            "rating_array",
            "internal_feedback_url",
            "external_feedback_url",
            "form",
            "prefilled_rating",
            "mode",
            "review_show_etablissement_pill",
            "review_accent_color",
        }
        self.assertEqual(set(ctx.keys()), expected_keys)

    def test_rating_array_reflects_threshold(self):
        ctx = build_feedback_context(self.etab, str(self.etab.slug))

        # threshold=4, so stars 1-3 are False, 4-5 are True
        self.assertEqual(ctx["rating_array"], [False, False, False, True, True])

    def test_mode_defaults_to_main(self):
        ctx = build_feedback_context(self.etab, str(self.etab.slug))

        self.assertEqual(ctx["mode"], "main")

    def test_accent_color_uses_etablissement_value(self):
        ctx = build_feedback_context(self.etab, str(self.etab.slug))

        self.assertEqual(ctx["review_accent_color"], "#ff0000")
