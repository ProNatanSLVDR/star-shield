from django import forms

from apps.private.auths import choices


class QRCodeCreateForm(forms.Form):
    """Form for creating a new QR code (only name and routing)."""

    name = forms.CharField(
        max_length=255,
        required=True,
        label="Nom du QR code",
        help_text="Nom pour identifier ce QR code.",
    )
    routing = forms.ChoiceField(
        choices=choices.QR_ROUTING_CHOICES,
        required=True,
        label="Destination",
        help_text="Où ce QR code redirige les utilisateurs.",
    )


class QRCodeSettingsForm(forms.Form):
    """Form for editing an existing QR code."""

    name = forms.CharField(
        max_length=255,
        required=True,
        label="Nom du QR code",
        help_text="Nom pour identifier ce QR code.",
    )
    routing = forms.ChoiceField(
        choices=choices.QR_ROUTING_CHOICES,
        required=True,
        label="Destination",
        help_text="Où ce QR code redirige les utilisateurs.",
    )
    qr_fill_color = forms.CharField(
        max_length=7,
        required=True,
        label="Couleur primaire",
    )
    qr_fill_color_secondary = forms.CharField(
        max_length=7,
        required=True,
        label="Couleur secondaire",
    )
    qr_background_color = forms.CharField(
        max_length=7,
        required=True,
        label="Couleur de fond",
    )
    qr_style = forms.ChoiceField(
        choices=choices.QR_STYLE_CHOICES,
        required=True,
        label="Style",
    )
    qr_color_mask = forms.ChoiceField(
        choices=choices.QR_COLOR_MASK_CHOICES,
        required=True,
        label="Style de couleur",
    )
    qr_logo = forms.ImageField(
        required=False,
        label="Logo",
        help_text="Logo à afficher au centre du QR code.",
    )
