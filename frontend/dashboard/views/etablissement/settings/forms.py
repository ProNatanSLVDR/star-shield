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
