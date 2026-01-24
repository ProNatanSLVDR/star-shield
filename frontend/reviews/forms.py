from django import forms
from django.utils.translation import gettext_lazy as _


class FeedbackForm(forms.Form):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
        error_messages={
            "required": _("Sélectionnez une note entre 1 et 5 étoiles."),
            "min_value": _("La note doit être au minimum de 1 étoile."),
            "max_value": _("La note ne peut pas dépasser 5 étoiles."),
        },
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": _("Partagez-nous plus de détails..."),
            }
        ),
        max_length=2000,
    )

    def clean_comment(self):
        comment = self.cleaned_data.get("comment", "")
        return comment.strip()
