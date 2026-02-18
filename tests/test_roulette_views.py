from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.public.roulette.models import RouletteAnalytics, RouletteSpin
from apps.public.roulette.views import generate_prize_code, is_in_cooldown
from tests.factories import EtablissementFactory, RoulettePrizeFactory, RouletteSpinFactory


class TestRouletteView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_renders_for_active_roulette(self):
        response = self.client.get(reverse("roulette:wheel", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 200)

    def test_redirects_when_inactive(self):
        self.etab.active = False
        self.etab.save(update_fields=["active"])

        response = self.client.get(reverse("roulette:wheel", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)

    def test_redirects_when_roulette_disabled(self):
        self.etab.roulette_enabled = False
        self.etab.save(update_fields=["roulette_enabled"])

        response = self.client.get(reverse("roulette:wheel", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)

    def test_creates_analytics_on_visit(self):
        self.client.get(reverse("roulette:wheel", args=[self.etab.slug]))

        self.assertEqual(
            RouletteAnalytics.objects.filter(etablissement=self.etab, type="roulette_viewed").count(),
            1,
        )


class TestSpinRouletteView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_creates_spin_record_for_prize(self):
        RoulettePrizeFactory(
            etablissement=self.etab,
            name="Free Coffee",
            probability=Decimal("100.00"),
            is_nothing_prize=False,
        )

        response = self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            RouletteSpin.objects.filter(etablissement=self.etab).count(),
            1,
        )

    def test_sets_cooldown_cookie(self):
        RoulettePrizeFactory(
            etablissement=self.etab,
            probability=Decimal("100.00"),
            is_nothing_prize=True,
        )

        response = self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        cookie_name = f"roulette_last_spin_{self.etab.id}"
        self.assertIn(cookie_name, response.cookies)

    def test_redirects_when_roulette_disabled(self):
        self.etab.roulette_enabled = False
        self.etab.save(update_fields=["roulette_enabled"])

        response = self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)

    def test_no_prize_creates_analytics(self):
        RoulettePrizeFactory(
            etablissement=self.etab,
            probability=Decimal("100.00"),
            is_nothing_prize=True,
        )

        self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertTrue(RouletteAnalytics.objects.filter(etablissement=self.etab, type="no_prize").exists())


class TestVerifyCodeView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_renders_with_valid_code(self):
        spin = RouletteSpinFactory(etablissement=self.etab, is_used=False)

        response = self.client.get(reverse("roulette:verify", args=[self.etab.slug, spin.prize_code]))

        self.assertEqual(response.status_code, 200)

    def test_renders_without_code(self):
        response = self.client.get(reverse("roulette:verify", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 200)

    def test_redirects_when_inactive(self):
        self.etab.active = False
        self.etab.save(update_fields=["active"])

        response = self.client.get(reverse("roulette:verify", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)


class TestRedeemCodeView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_marks_code_as_used(self):
        spin = RouletteSpinFactory(etablissement=self.etab, is_used=False)

        response = self.client.post(
            reverse("roulette:redeem", args=[self.etab.slug]),
            data={"code": spin.prize_code},
        )

        self.assertEqual(response.status_code, 302)
        spin.refresh_from_db()
        self.assertTrue(spin.is_used)

    def test_does_not_reredeem_used_code(self):
        spin = RouletteSpinFactory(etablissement=self.etab, is_used=True)

        self.client.post(
            reverse("roulette:redeem", args=[self.etab.slug]),
            data={"code": spin.prize_code},
        )

        spin.refresh_from_db()
        self.assertTrue(spin.is_used)

    def test_invalid_form_redirects(self):
        response = self.client.post(
            reverse("roulette:redeem", args=[self.etab.slug]),
            data={},
        )

        self.assertEqual(response.status_code, 302)

    def test_redirects_when_inactive(self):
        self.etab.active = False
        self.etab.save(update_fields=["active"])

        response = self.client.post(
            reverse("roulette:redeem", args=[self.etab.slug]),
            data={"code": "ABC123"},
        )

        self.assertEqual(response.status_code, 302)


class TestRouletteViewPreview(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_preview_mode_no_analytics(self):
        self.client.get(
            reverse("roulette:wheel", args=[self.etab.slug]),
            {"preview": "true"},
        )

        self.assertEqual(
            RouletteAnalytics.objects.filter(etablissement=self.etab, type="roulette_viewed").count(),
            0,
        )

    def test_preview_mode_renders(self):
        response = self.client.get(
            reverse("roulette:wheel", args=[self.etab.slug]),
            {"preview": "true"},
        )

        self.assertEqual(response.status_code, 200)


class TestRouletteCooldown(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True, roulette_spin_cooldown_days=14)

    def test_cooldown_redirects_spin(self):
        # Set cooldown cookie
        cookie_name = f"roulette_last_spin_{self.etab.id}"
        self.client.cookies[cookie_name] = timezone.now().isoformat()

        response = self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("cooldown", response.url)

    def test_cooldown_redirects_wheel(self):
        cookie_name = f"roulette_last_spin_{self.etab.id}"
        self.client.cookies[cookie_name] = timezone.now().isoformat()

        response = self.client.get(reverse("roulette:wheel", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("cooldown", response.url)


class TestIsInCooldown(TestCase):
    def test_no_cookie_not_in_cooldown(self):
        from django.test import RequestFactory

        etab = EtablissementFactory(roulette_spin_cooldown_days=14)
        request = RequestFactory().get("/")
        request.COOKIES = {}

        self.assertFalse(is_in_cooldown(request, etab))

    def test_recent_cookie_in_cooldown(self):
        from django.test import RequestFactory

        etab = EtablissementFactory(roulette_spin_cooldown_days=14)
        request = RequestFactory().get("/")
        request.COOKIES = {f"roulette_last_spin_{etab.id}": timezone.now().isoformat()}

        self.assertTrue(is_in_cooldown(request, etab))

    def test_expired_cookie_not_in_cooldown(self):
        from datetime import timedelta

        from django.test import RequestFactory

        etab = EtablissementFactory(roulette_spin_cooldown_days=14)
        old_date = (timezone.now() - timedelta(days=30)).isoformat()
        request = RequestFactory().get("/")
        request.COOKIES = {f"roulette_last_spin_{etab.id}": old_date}

        self.assertFalse(is_in_cooldown(request, etab))

    def test_invalid_cookie_not_in_cooldown(self):
        from django.test import RequestFactory

        etab = EtablissementFactory(roulette_spin_cooldown_days=14)
        request = RequestFactory().get("/")
        request.COOKIES = {f"roulette_last_spin_{etab.id}": "not-a-date"}

        self.assertFalse(is_in_cooldown(request, etab))


class TestGeneratePrizeCode(TestCase):
    def test_generates_unique_code(self):
        etab = EtablissementFactory()
        code = generate_prize_code(etab)

        self.assertEqual(len(code), 6)
        self.assertTrue(code.isalnum())

    def test_raises_after_max_attempts(self):
        etab = EtablissementFactory()
        # Create a spin with every possible code (mock the check)
        with patch("apps.public.roulette.views.RouletteSpin.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = True

            with self.assertRaises(ValueError):
                generate_prize_code(etab)


class TestSpinRouletteNoPrizes(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_no_prizes_redirects_to_result(self):
        # No prizes configured
        response = self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("result", response.url)

    def test_prize_won_creates_analytics(self):
        RoulettePrizeFactory(
            etablissement=self.etab,
            probability=Decimal("100.00"),
            is_nothing_prize=False,
        )

        self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertTrue(RouletteAnalytics.objects.filter(etablissement=self.etab, type="prize_won").exists())

    def test_spin_creates_spin_analytics(self):
        RoulettePrizeFactory(
            etablissement=self.etab,
            probability=Decimal("100.00"),
            is_nothing_prize=True,
        )

        self.client.post(reverse("roulette:spin", args=[self.etab.slug]))

        self.assertTrue(RouletteAnalytics.objects.filter(etablissement=self.etab, type="roulette_spun").exists())


class TestRouletteCooldownView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_redirects_to_wheel_when_not_in_cooldown(self):
        response = self.client.get(reverse("roulette:cooldown", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("cooldown", response.url)

    def test_renders_when_in_cooldown(self):
        cookie_name = f"roulette_last_spin_{self.etab.id}"
        self.client.cookies[cookie_name] = timezone.now().isoformat()

        response = self.client.get(reverse("roulette:cooldown", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 200)

    def test_redirects_when_inactive(self):
        self.etab.active = False
        self.etab.save(update_fields=["active"])

        response = self.client.get(reverse("roulette:cooldown", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)


class TestRouletteResultView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True, roulette_enabled=True)

    def test_renders_without_prize_code(self):
        RoulettePrizeFactory(etablissement=self.etab, is_nothing_prize=True, probability=Decimal("100.00"))

        response = self.client.get(reverse("roulette:result", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 200)

    def test_renders_with_valid_prize_code(self):
        spin = RouletteSpinFactory(etablissement=self.etab)

        response = self.client.get(reverse("roulette:result", args=[self.etab.slug, spin.prize_code]))

        self.assertEqual(response.status_code, 200)

    def test_invalid_prize_code_treats_as_no_prize(self):
        RoulettePrizeFactory(etablissement=self.etab, is_nothing_prize=True, probability=Decimal("100.00"))

        response = self.client.get(reverse("roulette:result", args=[self.etab.slug, "INVALID"]))

        self.assertEqual(response.status_code, 200)

    def test_redirects_when_inactive(self):
        self.etab.active = False
        self.etab.save(update_fields=["active"])

        response = self.client.get(reverse("roulette:result", args=[self.etab.slug]))

        self.assertEqual(response.status_code, 302)
