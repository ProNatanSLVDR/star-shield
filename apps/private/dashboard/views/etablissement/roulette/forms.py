from django import forms

# FontAwesome icon choices for roulette prizes
ROULETTE_ICON_CHOICES = [
    ("fa-solid fa-gift", "Cadeau"),
    ("fa-solid fa-trophy", "Trophée"),
    ("fa-solid fa-star", "Étoile"),
    ("fa-solid fa-pizza-slice", "Pizza"),
    ("fa-solid fa-utensils", "Couverts"),
    ("fa-solid fa-wine-glass", "Verre de vin"),
    ("fa-solid fa-cake", "Gâteau"),
    ("fa-solid fa-coffee", "Café"),
    ("fa-solid fa-burger", "Burger"),
    ("fa-solid fa-ice-cream", "Glace"),
    ("fa-solid fa-cookie", "Cookie"),
    ("fa-solid fa-martini-glass", "Cocktail"),
    ("fa-solid fa-champagne-glasses", "Champagne"),
    ("fa-solid fa-apple-whole", "Pomme"),
    ("fa-solid fa-bowl-food", "Bol"),
    ("fa-solid fa-fish", "Poisson"),
    ("fa-solid fa-drumstick-bite", "Poulet"),
    ("fa-solid fa-pepper-hot", "Piment"),
]


class RoulettePrizeForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        required=True,
        label="Nom du prix",
        help_text="Nom du prix à afficher sur la roue",
    )
    icon = forms.ChoiceField(
        choices=ROULETTE_ICON_CHOICES,
        required=True,
        label="Icône",
        help_text="Selectionnez l'icône à afficher sur la roue",
    )
    probability = forms.IntegerField(
        min_value=1,
        max_value=100,
        required=True,
        label="Probabilité (%)",
        help_text="Probabilité de gagner ce prix. Le prix 'Rien' sera automatiquement ajusté.",
    )


class RouletteSettingsForm(forms.Form):
    roulette_spin_cooldown_days = forms.IntegerField(
        min_value=1,
        required=True,
        label="Délai entre deux spins (en jours)",
        initial=14,
    )
