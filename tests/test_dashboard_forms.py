from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.private.dashboard.views.etablissement.ai_responses.forms import (
    AiResponseSettingsForm,
    ApproveReviewForm,
)
from apps.private.dashboard.views.etablissement.filtre.forms import (
    ReviewSettingsForm,
    ThresholdObjectiveForm,
)
from apps.private.dashboard.views.etablissement.forms import (
    QRCodeCreateForm,
    QRCodeSettingsForm,
)
from apps.private.dashboard.views.etablissement.roulette.forms import (
    RoulettePrizeForm,
    RouletteSettingsForm,
)
from apps.private.dashboard.views.etablissement.settings.forms import (
    EtablissementSettingsForm,
    ToggleFeatureForm,
)
from apps.private.dashboard.views.etablissements.forms import (
    ImportEtablissementForm,
    ToggleEtablissementStatusForm,
)
from apps.private.dashboard.views.profile.forms import (
    ProfilePictureForm,
    UserProfileForm,
)


class TestImportEtablissementForm(SimpleTestCase):
    def _locations(self):
        return [
            {"name": "loc/1", "title": "Shop 1", "exists": False},
            {"name": "loc/2", "title": "Shop 2", "exists": True},
        ]

    def test_valid_selection(self):
        form = ImportEtablissementForm(
            data={"locations": ["loc/1"]},
            available_locations=self._locations(),
        )
        self.assertTrue(form.is_valid())

    def test_existing_location_excluded_from_choices(self):
        form = ImportEtablissementForm(available_locations=self._locations())
        choice_values = [c[0] for c in form.fields["locations"].choices]
        self.assertIn("loc/1", choice_values)
        self.assertNotIn("loc/2", choice_values)

    def test_required_field(self):
        form = ImportEtablissementForm(data={}, available_locations=self._locations())
        self.assertFalse(form.is_valid())
        self.assertIn("locations", form.errors)

    def test_invalid_choice_rejected(self):
        form = ImportEtablissementForm(
            data={"locations": ["loc/999"]},
            available_locations=self._locations(),
        )
        self.assertFalse(form.is_valid())


class TestToggleEtablissementStatusForm(SimpleTestCase):
    @patch("apps.private.dashboard.views.etablissements.forms.settings")
    def test_valid_price_id(self, mock_settings):
        mock_settings.STRIPE_PRODUCTS = {
            "basic_subscription": {"monthly": "price_monthly", "trimestrial": "price_tri", "yearly": "price_yearly"}
        }
        form = ToggleEtablissementStatusForm(data={"price_id": "price_monthly"})
        self.assertTrue(form.is_valid())

    @patch("apps.private.dashboard.views.etablissements.forms.settings")
    def test_invalid_price_id(self, mock_settings):
        mock_settings.STRIPE_PRODUCTS = {
            "basic_subscription": {"monthly": "price_monthly", "trimestrial": "price_tri", "yearly": "price_yearly"}
        }
        form = ToggleEtablissementStatusForm(data={"price_id": "price_unknown"})
        self.assertFalse(form.is_valid())
        self.assertIn("price_id", form.errors)

    def test_empty_price_id(self):
        form = ToggleEtablissementStatusForm(data={"price_id": ""})
        self.assertFalse(form.is_valid())


class TestQRCodeCreateForm(SimpleTestCase):
    def test_valid_data(self):
        form = QRCodeCreateForm(data={"name": "Mon QR", "routing": "feedback"})
        self.assertTrue(form.is_valid())

    def test_missing_name(self):
        form = QRCodeCreateForm(data={"name": "", "routing": "feedback"})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_invalid_routing(self):
        form = QRCodeCreateForm(data={"name": "QR", "routing": "invalid"})
        self.assertFalse(form.is_valid())
        self.assertIn("routing", form.errors)

    def test_all_routing_choices(self):
        for routing in ["feedback", "roulette", "verify"]:
            form = QRCodeCreateForm(data={"name": "QR", "routing": routing})
            self.assertTrue(form.is_valid(), f"routing={routing} should be valid")


class TestQRCodeSettingsForm(SimpleTestCase):
    def _valid_data(self, **overrides):
        data = {
            "name": "QR Code",
            "routing": "feedback",
            "qr_fill_color": "#000000",
            "qr_fill_color_secondary": "#111111",
            "qr_background_color": "#FFFFFF",
            "qr_style": "square",
            "qr_color_mask": "solid",
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = QRCodeSettingsForm(data=self._valid_data())
        self.assertTrue(form.is_valid())

    def test_invalid_hex_color(self):
        form = QRCodeSettingsForm(data=self._valid_data(qr_fill_color="red"))
        self.assertFalse(form.is_valid())
        self.assertIn("qr_fill_color", form.errors)

    def test_invalid_hex_too_short(self):
        form = QRCodeSettingsForm(data=self._valid_data(qr_fill_color="#FFF"))
        self.assertFalse(form.is_valid())

    def test_invalid_style_choice(self):
        form = QRCodeSettingsForm(data=self._valid_data(qr_style="dotted"))
        self.assertFalse(form.is_valid())
        self.assertIn("qr_style", form.errors)


class TestEtablissementSettingsForm(SimpleTestCase):
    def test_valid_data(self):
        form = EtablissementSettingsForm(data={"title": "Mon Resto", "target_rating": "4.50"})
        self.assertTrue(form.is_valid())

    def test_title_required(self):
        form = EtablissementSettingsForm(data={"title": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_target_rating_optional(self):
        form = EtablissementSettingsForm(data={"title": "Mon Resto"})
        self.assertTrue(form.is_valid())

    def test_target_rating_below_min(self):
        form = EtablissementSettingsForm(data={"title": "X", "target_rating": "2.00"})
        self.assertFalse(form.is_valid())
        self.assertIn("target_rating", form.errors)

    def test_target_rating_above_max(self):
        form = EtablissementSettingsForm(data={"title": "X", "target_rating": "5.50"})
        self.assertFalse(form.is_valid())
        self.assertIn("target_rating", form.errors)


class TestToggleFeatureForm(SimpleTestCase):
    def test_all_on(self):
        form = ToggleFeatureForm(
            data={
                "review_filtering_enabled": True,
                "roulette_enabled": True,
                "ai_responses_enabled": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_all_off(self):
        form = ToggleFeatureForm(data={})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["review_filtering_enabled"])
        self.assertFalse(form.cleaned_data["roulette_enabled"])
        self.assertFalse(form.cleaned_data["ai_responses_enabled"])


class TestRoulettePrizeForm(SimpleTestCase):
    def test_valid_data(self):
        form = RoulettePrizeForm(
            data={"name": "Café gratuit", "icon": "fa-solid fa-coffee", "probability": "25.00"}
        )
        self.assertTrue(form.is_valid())

    def test_probability_zero_rejected(self):
        form = RoulettePrizeForm(
            data={"name": "Prix", "icon": "fa-solid fa-gift", "probability": "0"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("probability", form.errors)

    def test_probability_over_100_rejected(self):
        form = RoulettePrizeForm(
            data={"name": "Prix", "icon": "fa-solid fa-gift", "probability": "101"}
        )
        self.assertFalse(form.is_valid())

    def test_minimum_probability(self):
        form = RoulettePrizeForm(
            data={"name": "Prix", "icon": "fa-solid fa-gift", "probability": "0.01"}
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["probability"], Decimal("0.01"))

    def test_invalid_icon_choice(self):
        form = RoulettePrizeForm(
            data={"name": "Prix", "icon": "fa-solid fa-invalid", "probability": "10"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("icon", form.errors)


class TestRouletteSettingsForm(SimpleTestCase):
    def test_valid_data(self):
        form = RouletteSettingsForm(data={"roulette_spin_cooldown_days": 14})
        self.assertTrue(form.is_valid())

    def test_min_value_1(self):
        form = RouletteSettingsForm(data={"roulette_spin_cooldown_days": 0})
        self.assertFalse(form.is_valid())

    def test_required(self):
        form = RouletteSettingsForm(data={})
        self.assertFalse(form.is_valid())


class TestThresholdObjectiveForm(SimpleTestCase):
    def test_valid_choices(self):
        for val in [3, 4, 5]:
            form = ThresholdObjectiveForm(data={"review_threshold": val})
            self.assertTrue(form.is_valid(), f"threshold={val} should be valid")

    def test_invalid_choice(self):
        form = ThresholdObjectiveForm(data={"review_threshold": 2})
        self.assertFalse(form.is_valid())

    def test_required(self):
        form = ThresholdObjectiveForm(data={})
        self.assertFalse(form.is_valid())


class TestReviewSettingsForm(SimpleTestCase):
    def test_valid_data(self):
        form = ReviewSettingsForm(data={"review_accent_color": "#FF5733"})
        self.assertTrue(form.is_valid())

    def test_invalid_hex_color(self):
        form = ReviewSettingsForm(data={"review_accent_color": "blue"})
        self.assertFalse(form.is_valid())

    def test_optional_fields(self):
        form = ReviewSettingsForm(
            data={
                "review_accent_color": "#000000",
                "review_page_label": "Laissez un avis",
                "review_page_text": "Merci !",
            }
        )
        self.assertTrue(form.is_valid())


class TestAiResponseSettingsForm(SimpleTestCase):
    def _valid_data(self, **overrides):
        data = {
            "ai_response_tone": "professionnel",
            "ai_response_length": "medium",
            "ai_response_language": "fr",
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = AiResponseSettingsForm(data=self._valid_data())
        self.assertTrue(form.is_valid())

    def test_invalid_tone(self):
        form = AiResponseSettingsForm(data=self._valid_data(ai_response_tone="angry"))
        self.assertFalse(form.is_valid())

    def test_invalid_length(self):
        form = AiResponseSettingsForm(data=self._valid_data(ai_response_length="tiny"))
        self.assertFalse(form.is_valid())

    def test_invalid_language(self):
        form = AiResponseSettingsForm(data=self._valid_data(ai_response_language="de"))
        self.assertFalse(form.is_valid())

    def test_boolean_fields_optional(self):
        form = AiResponseSettingsForm(data=self._valid_data())
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["ai_response_validation_required"])
        self.assertFalse(form.cleaned_data["ai_response_malicious_protection"])

    def test_boolean_fields_on(self):
        form = AiResponseSettingsForm(
            data=self._valid_data(
                ai_response_validation_required=True,
                ai_response_malicious_protection=True,
            )
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["ai_response_validation_required"])


class TestApproveReviewForm(SimpleTestCase):
    def test_empty_is_valid(self):
        form = ApproveReviewForm(data={})
        self.assertTrue(form.is_valid())

    def test_with_comment(self):
        form = ApproveReviewForm(data={"edited_comment": "Merci !"})
        self.assertTrue(form.is_valid())

    def test_max_length(self):
        form = ApproveReviewForm(data={"edited_comment": "x" * 2001})
        self.assertFalse(form.is_valid())


class TestUserProfileForm(SimpleTestCase):
    def test_valid_data(self):
        form = UserProfileForm(data={"first_name": "Jean", "last_name": "Dupont"})
        self.assertTrue(form.is_valid())

    def test_empty_is_valid(self):
        form = UserProfileForm(data={})
        self.assertTrue(form.is_valid())


class TestProfilePictureForm(SimpleTestCase):
    def test_delete_flag(self):
        form = ProfilePictureForm(data={"delete_profile_picture": True})
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["delete_profile_picture"])

    def test_empty_is_valid(self):
        form = ProfilePictureForm(data={})
        self.assertTrue(form.is_valid())
