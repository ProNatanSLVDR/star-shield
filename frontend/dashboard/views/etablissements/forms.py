from django import forms
from django.conf import settings
from typing import List, Dict, Any, Optional


class ImportEtablissementForm(forms.Form):
    locations = forms.MultipleChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        available_locations = kwargs.pop("available_locations", [])
        super().__init__(*args, **kwargs)

        # On crée un dictionnaire des locations disponibles
        choices = []
        for location in available_locations:
            if not location["exists"]:
                choices.append((location["name"], location["title"]))
        self.fields["locations"].choices = choices


class ToggleEtablissementStatusForm(forms.Form):
    price_id = forms.CharField(required=True)

    def clean_price_id(self):
        price_id = self.cleaned_data.get("price_id")

        if not price_id:
            raise forms.ValidationError("Le plan d'abonnement est requis.")

        allowed_prices = [
            settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("monthly"),
            settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("yearly"),
        ]

        # Filter out None values in case a price is not configured
        allowed_prices = [p for p in allowed_prices if p]

        if price_id not in allowed_prices:
            raise forms.ValidationError("Le plan d'abonnement sélectionné n'est pas valide.")

        return price_id
