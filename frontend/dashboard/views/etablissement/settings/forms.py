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


class ToggleFeatureForm(forms.Form):
    # These fields are optional - they're only present when checkboxes are checked
    # We'll check them directly from POST data since unchecked checkboxes don't send values
    review_filtering_enabled = forms.CharField(required=False)
    roulette_enabled = forms.CharField(required=False)
