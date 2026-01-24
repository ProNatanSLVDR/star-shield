from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator


class EtablissementSettingsForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        required=True,
    )
    target_rating = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(3), MaxValueValidator(5)],
    )
    review_filtering_enabled = forms.BooleanField(
        required=False,
    )
    roulette_enabled = forms.BooleanField(
        required=False,
    )
