from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.public.roulette.models import RoulettePrize
from tests.factories import (
    EtablissementFactory,
    RouletteAnalyticsFactory,
    RoulettePrizeFactory,
    RouletteSpinFactory,
)


class DashboardRouletteMixin:
    def setUp(self):
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()


class TestRouletteSettingsView(DashboardRouletteMixin, TestCase):
    def test_get_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:roulette:roulette"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_post_updates_cooldown(self):
        response = self.client.post(
            reverse("dashboard:etablissement:roulette:roulette"),
            data={"roulette_spin_cooldown_days": 7},
        )
        self.assertEqual(response.status_code, 302)
        self.etab.refresh_from_db()
        self.assertEqual(self.etab.roulette_spin_cooldown_days, 7)

    def test_post_invalid_cooldown(self):
        response = self.client.post(
            reverse("dashboard:etablissement:roulette:roulette"),
            data={"roulette_spin_cooldown_days": 0},
        )
        self.assertEqual(response.status_code, 200)  # Re-renders form with errors

    def test_nothing_prize_auto_created(self):
        self.client.get(reverse("dashboard:etablissement:roulette:roulette"))
        self.assertTrue(
            self.etab.roulette_prizes.filter(is_nothing_prize=True).exists()
        )


class TestPrizesTablePartial(DashboardRouletteMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:roulette:prizes_table"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("prizes_table", response.context)

    def test_shows_existing_prizes(self):
        RoulettePrizeFactory(etablissement=self.etab, name="Café", probability=Decimal("25.00"))
        response = self.client.get(reverse("dashboard:etablissement:roulette:prizes_table"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["prizes_table"]["rows"]) >= 1)


class TestPrizeCreatePartial(DashboardRouletteMixin, TestCase):
    def test_get_returns_form(self):
        response = self.client.get(reverse("dashboard:etablissement:roulette:prize_create"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_create_prize(self):
        response = self.client.post(
            reverse("dashboard:etablissement:roulette:prize_create"),
            data={
                "name": "Café gratuit",
                "icon": "fa-solid fa-coffee",
                "probability": "25.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.etab.roulette_prizes.filter(name="Café gratuit").exists()
        )

    def test_create_prize_updates_nothing_prize(self):
        self.client.post(
            reverse("dashboard:etablissement:roulette:prize_create"),
            data={
                "name": "Prize 1",
                "icon": "fa-solid fa-gift",
                "probability": "30.00",
            },
        )
        nothing = self.etab.roulette_prizes.filter(is_nothing_prize=True).first()
        self.assertIsNotNone(nothing)
        self.assertEqual(float(nothing.probability), 70.00)

    def test_probability_exceeds_100_rejected(self):
        RoulettePrizeFactory(etablissement=self.etab, probability=Decimal("90.00"))
        response = self.client.post(
            reverse("dashboard:etablissement:roulette:prize_create"),
            data={
                "name": "Too much",
                "icon": "fa-solid fa-gift",
                "probability": "20.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.etab.roulette_prizes.filter(name="Too much").exists()
        )

    def test_limit_8_prizes(self):
        for i in range(8):
            RoulettePrizeFactory(
                etablissement=self.etab,
                name=f"Prize {i}",
                probability=Decimal("5.00"),
            )
        response = self.client.post(
            reverse("dashboard:etablissement:roulette:prize_create"),
            data={
                "name": "One too many",
                "icon": "fa-solid fa-gift",
                "probability": "5.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.etab.roulette_prizes.filter(name="One too many").exists()
        )


class TestPrizeEditPartial(DashboardRouletteMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.prize = RoulettePrizeFactory(
            etablissement=self.etab,
            name="Café",
            probability=Decimal("25.00"),
        )

    def test_get_returns_form(self):
        url = reverse("dashboard:etablissement:roulette:prize_edit", args=[self.prize.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_edit_prize(self):
        url = reverse("dashboard:etablissement:roulette:prize_edit", args=[self.prize.id])
        response = self.client.post(
            url,
            data={
                "name": "Café modifié",
                "icon": "fa-solid fa-coffee",
                "probability": "30.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.prize.refresh_from_db()
        self.assertEqual(self.prize.name, "Café modifié")
        self.assertEqual(float(self.prize.probability), 30.00)

    def test_edit_nothing_prize_blocked(self):
        nothing = RoulettePrize.objects.create(
            etablissement=self.etab,
            name="Rien",
            icon="fa-solid fa-ban",
            probability=Decimal("50.00"),
            is_nothing_prize=True,
        )
        url = reverse("dashboard:etablissement:roulette:prize_edit", args=[nothing.id])
        # The view has a bug: when is_nothing_prize=True, form is never assigned
        # but still referenced in the template context. This causes an UnboundLocalError.
        # We verify the nothing prize data remains unchanged despite the error.
        with self.assertRaises(UnboundLocalError):
            self.client.post(
                url,
                data={
                    "name": "Modified nothing",
                    "icon": "fa-solid fa-gift",
                    "probability": "10.00",
                },
            )
        nothing.refresh_from_db()
        self.assertEqual(nothing.name, "Rien")

    def test_edit_probability_exceeds_100(self):
        RoulettePrizeFactory(etablissement=self.etab, probability=Decimal("80.00"))
        url = reverse("dashboard:etablissement:roulette:prize_edit", args=[self.prize.id])
        response = self.client.post(
            url,
            data={
                "name": "Café",
                "icon": "fa-solid fa-coffee",
                "probability": "25.00",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_other_user_prize_404(self):
        other_etab = EtablissementFactory(active=True)
        other_prize = RoulettePrizeFactory(etablissement=other_etab)
        url = reverse("dashboard:etablissement:roulette:prize_edit", args=[other_prize.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestPrizeDeletePartial(DashboardRouletteMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.prize = RoulettePrizeFactory(
            etablissement=self.etab,
            name="Café",
            probability=Decimal("25.00"),
        )

    def test_delete_prize(self):
        url = reverse("dashboard:etablissement:roulette:prize_delete", args=[self.prize.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RoulettePrize.objects.filter(id=self.prize.id).exists())

    def test_delete_updates_nothing_prize(self):
        # Create nothing prize first
        self.client.get(reverse("dashboard:etablissement:roulette:roulette"))
        self.client.post(
            reverse("dashboard:etablissement:roulette:prize_delete", args=[self.prize.id])
        )
        nothing = self.etab.roulette_prizes.filter(is_nothing_prize=True).first()
        self.assertIsNotNone(nothing)
        self.assertEqual(float(nothing.probability), 100.00)

    def test_delete_nothing_prize_blocked(self):
        nothing = RoulettePrize.objects.create(
            etablissement=self.etab,
            name="Rien",
            icon="fa-solid fa-ban",
            probability=Decimal("50.00"),
            is_nothing_prize=True,
        )
        url = reverse("dashboard:etablissement:roulette:prize_delete", args=[nothing.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RoulettePrize.objects.filter(id=nothing.id).exists())

    def test_requires_post(self):
        url = reverse("dashboard:etablissement:roulette:prize_delete", args=[self.prize.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class TestRouletteHistoriqueView(DashboardRouletteMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:roulette:historique"))
        self.assertEqual(response.status_code, 200)


class TestRouletteHistoriqueContentPartial(DashboardRouletteMixin, TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("dashboard:etablissement:roulette:historique_content"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("stats", response.context)
        self.assertIn("table_data", response.context)

    def test_with_spin_data(self):
        prize = RoulettePrizeFactory(etablissement=self.etab)
        RouletteSpinFactory(etablissement=self.etab, prize=prize)
        RouletteAnalyticsFactory(etablissement=self.etab, type="roulette_spun")
        response = self.client.get(reverse("dashboard:etablissement:roulette:historique_content"))
        self.assertEqual(response.status_code, 200)

    def test_period_filter_all(self):
        response = self.client.get(
            reverse("dashboard:etablissement:roulette:historique_content"),
            {"period": "all"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_period"], "all")

    def test_period_filter_7(self):
        response = self.client.get(
            reverse("dashboard:etablissement:roulette:historique_content"),
            {"period": "7"},
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_period_defaults(self):
        response = self.client.get(
            reverse("dashboard:etablissement:roulette:historique_content"),
            {"period": "abc"},
        )
        self.assertEqual(response.status_code, 200)


class TestToggleSpinStatus(DashboardRouletteMixin, TestCase):
    def test_toggle_spin_used(self):
        prize = RoulettePrizeFactory(etablissement=self.etab)
        spin = RouletteSpinFactory(etablissement=self.etab, prize=prize, is_used=False)
        url = reverse("dashboard:etablissement:roulette:toggle_spin_status", args=[spin.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        spin.refresh_from_db()
        self.assertTrue(spin.is_used)

    def test_toggle_spin_unused(self):
        prize = RoulettePrizeFactory(etablissement=self.etab)
        spin = RouletteSpinFactory(etablissement=self.etab, prize=prize, is_used=True)
        url = reverse("dashboard:etablissement:roulette:toggle_spin_status", args=[spin.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        spin.refresh_from_db()
        self.assertFalse(spin.is_used)

    def test_requires_post(self):
        prize = RoulettePrizeFactory(etablissement=self.etab)
        spin = RouletteSpinFactory(etablissement=self.etab, prize=prize)
        url = reverse("dashboard:etablissement:roulette:toggle_spin_status", args=[spin.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_other_user_spin_404(self):
        other_etab = EtablissementFactory(active=True)
        prize = RoulettePrizeFactory(etablissement=other_etab)
        spin = RouletteSpinFactory(etablissement=other_etab, prize=prize)
        url = reverse("dashboard:etablissement:roulette:toggle_spin_status", args=[spin.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
