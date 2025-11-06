from django import forms


class EtablissementSettingsForm(forms.Form):
    review_threshold = forms.ChoiceField(
        choices=[(i, f"{i}★") for i in range(1, 6)],
        required=True,
        help_text="Note minimale pour redirection Google.",
        label="Seuil de redirection",
        widget=forms.Select(attrs={"class": "form-select"}),
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

