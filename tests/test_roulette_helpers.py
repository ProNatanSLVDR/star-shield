from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.public.roulette.views import calculate_prize, generate_prize_code, is_in_cooldown
from tests.factories import EtablissementFactory, RoulettePrizeFactory


class TestGeneratePrizeCode(TestCase):
    def test_returns_6_char_code(self):
        etab = EtablissementFactory()
        code = generate_prize_code(etab)
        self.assertEqual(len(code), 6)

    def test_returns_alphanumeric_code(self):
        etab = EtablissementFactory()
        code = generate_prize_code(etab)
        self.assertTrue(code.isalnum())

    def test_returns_uppercase_code(self):
        etab = EtablissementFactory()
        code = generate_prize_code(etab)
        self.assertEqual(code, code.upper())

    def test_raises_after_max_attempts(self):
        etab = EtablissementFactory()
        # Make every generated code already exist
        with patch("apps.public.roulette.views.RouletteSpin.objects") as mock_qs:
            mock_qs.filter.return_value.exists.return_value = True
            with self.assertRaises(ValueError, msg="Failed to generate unique prize code"):
                generate_prize_code(etab)


class TestCalculatePrize(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory()

    def test_returns_none_when_no_prizes(self):
        result = calculate_prize(self.etab)
        self.assertIsNone(result)

    @patch("apps.public.roulette.views.random.uniform")
    def test_selects_prize_based_on_probability(self, mock_uniform):
        prize1 = RoulettePrizeFactory(etablissement=self.etab, probability=Decimal("30.00"), name="Prize A")
        prize2 = RoulettePrizeFactory(etablissement=self.etab, probability=Decimal("70.00"), name="Prize B")

        # Random value 25 -> should select Prize A (cumulative 30)
        mock_uniform.return_value = 25.0
        result = calculate_prize(self.etab)
        self.assertEqual(result, prize1)

        # Random value 50 -> should select Prize B (cumulative 100)
        mock_uniform.return_value = 50.0
        result = calculate_prize(self.etab)
        self.assertEqual(result, prize2)

    @patch("apps.public.roulette.views.random.uniform")
    def test_falls_back_to_last_prize(self, mock_uniform):
        RoulettePrizeFactory(etablissement=self.etab, probability=Decimal("50.00"), name="Only Prize")

        # Random value beyond cumulative probability
        mock_uniform.return_value = 99.0
        result = calculate_prize(self.etab)
        # Should fallback to last prize
        self.assertIsNotNone(result)


class TestIsInCooldown(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory(roulette_spin_cooldown_days=14)

    def test_returns_false_when_no_cookie(self):
        request = MagicMock()
        request.COOKIES = {}
        result = is_in_cooldown(request, self.etab)
        self.assertFalse(result)

    def test_returns_true_when_in_cooldown(self):
        request = MagicMock()
        recent_spin = timezone.now().isoformat()
        request.COOKIES = {f"roulette_last_spin_{self.etab.id}": recent_spin}
        result = is_in_cooldown(request, self.etab)
        self.assertTrue(result)

    def test_returns_false_when_cooldown_expired(self):
        request = MagicMock()
        old_spin = (timezone.now() - timezone.timedelta(days=30)).isoformat()
        request.COOKIES = {f"roulette_last_spin_{self.etab.id}": old_spin}
        result = is_in_cooldown(request, self.etab)
        self.assertFalse(result)

    def test_returns_false_on_invalid_cookie_format(self):
        request = MagicMock()
        request.COOKIES = {f"roulette_last_spin_{self.etab.id}": "not-a-date"}
        result = is_in_cooldown(request, self.etab)
        self.assertFalse(result)
