from django import forms

from apps.private.auths import choices


class ThresholdObjectiveForm(forms.Form):
    review_threshold = forms.ChoiceField(
        choices=[(i, f"{i}★") for i in range(3, 6)],
        required=True,
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
