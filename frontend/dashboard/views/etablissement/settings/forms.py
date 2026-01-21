from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from auths import choices


class EtablissementSettingsForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        required=True,
    )
    review_threshold = forms.ChoiceField(
        choices=[(i, f"{i}★") for i in range(3, 6)],
        required=True,
    )
    target_rating = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )


class ReviewSettingsForm(forms.Form):
    review_accent_color = forms.CharField(
        max_length=7,
        required=True,
    )
    review_show_etablissement_pill = forms.ChoiceField(
        choices=[(True, "Oui"), (False, "Non")],
        required=False,
    )
    review_page_label = forms.CharField(
        max_length=255,
        required=False,
    )
    review_page_text = forms.CharField(
        max_length=255,
        required=False,
    )


class ThresholdObjectiveForm(forms.Form):
    review_threshold = forms.ChoiceField(
        choices=[(i, f"{i}★") for i in range(3, 6)],
        required=True,
    )
    target_rating = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )


class QRCodeSettingsForm(forms.Form):
    qr_fill_color = forms.CharField(
        max_length=7,
        required=True,
    )
    qr_fill_color_secondary = forms.CharField(
        max_length=7,
        required=True,
    )
    qr_background_color = forms.CharField(
        max_length=7,
        required=True,
    )
    qr_style = forms.ChoiceField(
        choices=choices.QR_STYLE_CHOICES,
        required=True,
    )
    qr_color_mask = forms.ChoiceField(
        choices=choices.QR_COLOR_MASK_CHOICES,
        required=True,
    )
    qr_logo = forms.ImageField(
        required=False,
        help_text="Logo à afficher au centre du QR code.",
    )


# FontAwesome icon choices for roulette prizes
ROULETTE_ICON_CHOICES = [
    ("fa-solid fa-gift", "Cadeau"),
    ("fa-solid fa-trophy", "Trophée"),
    ("fa-solid fa-star", "Étoile"),
    ("fa-solid fa-pizza-slice", "Pizza"),
    ("fa-solid fa-utensils", "Couverts"),
    ("fa-solid fa-wine-glass", "Verre de vin"),
    ("fa-solid fa-cake", "Gâteau"),
    ("fa-solid fa-coffee", "Café"),
    ("fa-solid fa-burger", "Burger"),
    ("fa-solid fa-ice-cream", "Glace"),
    ("fa-solid fa-cookie", "Cookie"),
    ("fa-solid fa-martini-glass", "Cocktail"),
    ("fa-solid fa-champagne-glasses", "Champagne"),
    ("fa-solid fa-birthday-cake", "Gâteau d'anniversaire"),
    ("fa-solid fa-bowl-food", "Bol"),
    ("fa-solid fa-fish", "Poisson"),
    ("fa-solid fa-drumstick-bite", "Poulet"),
    ("fa-solid fa-pepper-hot", "Piment"),
]


class RouletteSettingsForm(forms.Form):
    roulette_enabled = forms.BooleanField(
        required=False,
        label="Activer la roue de la fortune",
    )
    roulette_spin_cooldown_days = forms.IntegerField(
        min_value=1,
        required=True,
        label="Délai entre deux spins (en jours)",
        initial=14,
    )

    def __init__(self, *args, **kwargs):
        prizes_data = kwargs.pop("prizes_data", None)
        super().__init__(*args, **kwargs)

        if prizes_data:
            for i, prize in enumerate(prizes_data):
                self.fields[f"prize_{i}_id"] = forms.IntegerField(
                    required=False,
                    widget=forms.HiddenInput(),
                )
                self.fields[f"prize_{i}_name"] = forms.CharField(
                    max_length=255,
                    required=False,
                    label=f"Prix {i + 1} - Nom",
                )
                self.fields[f"prize_{i}_icon"] = forms.ChoiceField(
                    choices=ROULETTE_ICON_CHOICES,
                    required=False,
                    label=f"Prix {i + 1} - Icône",
                )
                self.fields[f"prize_{i}_probability"] = forms.DecimalField(
                    max_digits=5,
                    decimal_places=2,
                    min_value=1,
                    max_value=100,
                    required=False,
                    label=f"Prix {i + 1} - Probabilité (%)",
                )
                self.fields[f"prize_{i}_is_nothing"] = forms.BooleanField(
                    required=False,
                    label=f"Prix {i + 1} - 'Rien'",
                )

    def clean(self):
        cleaned_data = super().clean()

        # Collect all prize data
        prizes = []
        prize_count = 0

        i = 0
        while f"prize_{i}_name" in cleaned_data:
            name = cleaned_data.get(f"prize_{i}_name", "").strip()
            if name:  # Only include prizes with names
                icon = cleaned_data.get(f"prize_{i}_icon", "")
                probability = cleaned_data.get(f"prize_{i}_probability")
                is_nothing = cleaned_data.get(f"prize_{i}_is_nothing", False)
                prize_id = cleaned_data.get(f"prize_{i}_id")
                order = cleaned_data.get(f"prize_{i}_order", i)

                if not icon:
                    raise forms.ValidationError(f"L'icône est requise pour le prix '{name}'.")
                if probability is None:
                    raise forms.ValidationError(f"La probabilité est requise pour le prix '{name}'.")
                if probability < 1:
                    raise forms.ValidationError(f"La probabilité doit être d'au moins 1% pour le prix '{name}'.")

                prizes.append(
                    {
                        "id": prize_id,
                        "name": name,
                        "icon": icon,
                        "probability": probability,
                        "is_nothing": is_nothing,
                        "order": order,
                    }
                )
                prize_count += 1
            i += 1

        # Validate max 8 prizes
        if prize_count > 8:
            raise forms.ValidationError("Le maximum de 8 prix est autorisé (y compris le prix 'Rien').")

        # Validate probabilities sum to 100%
        total_probability = sum(p["probability"] for p in prizes)
        if prizes and abs(total_probability - 100.0) > 0.01:  # Allow small floating point errors
            raise forms.ValidationError(f"La somme des probabilités doit être exactement 100%. Actuellement: {total_probability}%")

        cleaned_data["prizes"] = prizes
        return cleaned_data
