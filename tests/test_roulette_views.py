from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.public.roulette.models import RouletteAnalytics, RouletteSpin
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
