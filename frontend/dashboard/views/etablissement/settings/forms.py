from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator


class EtablissementSettingsForm(forms.Form):
    review_threshold = forms.ChoiceField(
        choices=[(i, f"{i}★") for i in range(1, 6)],
        required=True,
        help_text="Note minimale pour redirection Google.",
        label="Seuil de redirection",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    target_rating = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Note cible que vous souhaitez atteindre à l'avenir.",
        label="Note cible",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "5"}
        ),
    )
    review_page_label = forms.CharField(
        max_length=255,
        required=False,
        help_text="Nom pour l'établissement sur la page de feedback.",
        label="Nom sur la page de feedback",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    review_page_text = forms.CharField(
        max_length=255,
        required=False,
        help_text="Texte à afficher sur la page de feedback.",
        label="Texte de la page de feedback",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ReviewSettingsForm(forms.Form):
    review_accent_color = forms.CharField(
        max_length=7,
        required=True,
    )
    review_show_etablissement_pill = forms.BooleanField(
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
