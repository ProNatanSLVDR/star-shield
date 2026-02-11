from django import forms

from apps.private.auths.choices import AI_LANGUAGE_CHOICES, AI_LENGTH_CHOICES, AI_TONE_CHOICES


class ApproveReviewForm(forms.Form):
    edited_comment = forms.CharField(
        required=False,
        max_length=2000,
        widget=forms.Textarea,
    )


class AiResponseSettingsForm(forms.Form):
    ai_response_tone = forms.ChoiceField(
        choices=AI_TONE_CHOICES,
        required=True,
        label="Ton de la réponse",
    )
    ai_response_length = forms.ChoiceField(
        choices=AI_LENGTH_CHOICES,
        required=True,
        label="Longueur de la réponse",
    )
    ai_response_language = forms.ChoiceField(
        choices=AI_LANGUAGE_CHOICES,
        required=True,
        label="Langue de la réponse",
    )
    ai_response_validation_required = forms.BooleanField(
        required=False,
        label="Validation manuelle",
    )
    ai_response_malicious_protection = forms.BooleanField(
        required=False,
        label="Protection avis malveillants",
    )
