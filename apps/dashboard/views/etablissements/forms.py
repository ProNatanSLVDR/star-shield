from django import forms
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