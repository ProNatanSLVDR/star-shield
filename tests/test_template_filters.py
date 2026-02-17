from django.test import SimpleTestCase

from apps.private.dashboard.templatetags.filters import after_original


class TestAfterOriginalFilter(SimpleTestCase):
    def test_extracts_text_after_original(self):
        value = "(Translated by Google) Bonjour (Original) Hello"
        result = after_original(value)
        self.assertEqual(result, "Hello")

    def test_returns_value_when_no_original_marker(self):
        value = "Just a regular comment"
        result = after_original(value)
        self.assertEqual(result, "Just a regular comment")

    def test_handles_none(self):
        result = after_original(None)
        self.assertIsNone(result)

    def test_handles_empty_string(self):
        result = after_original("")
        self.assertEqual(result, "")

    def test_strips_translated_by_google(self):
        value = "(Original) Le vrai texte (Translated by Google)"
        result = after_original(value)
        self.assertEqual(result, "Le vrai texte")

    def test_handles_both_markers(self):
        value = "(Translated by Google) Translated text (Original) Texte original (Translated by Google)"
        result = after_original(value)
        self.assertEqual(result, "Texte original")

    def test_only_translated_by_google_no_original(self):
        value = "Some text (Translated by Google) more text"
        result = after_original(value)
        self.assertEqual(result, "Some text")

    def test_strips_whitespace(self):
        value = "(Original)   Texte avec espaces   "
        result = after_original(value)
        self.assertEqual(result, "Texte avec espaces")
