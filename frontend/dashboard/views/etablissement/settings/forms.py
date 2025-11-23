from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator


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
    qr_background_color = forms.CharField(
        max_length=7,
        required=True,
    )
    qr_style = forms.ChoiceField(
        choices=[("square", "Carré"), ("rounded", "Arrondi")],
        required=True,
    )
    qr_logo = forms.ImageField(
        required=False,
        help_text="Logo à afficher au centre du QR code.",
    )
