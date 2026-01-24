from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from auths.models import Etablissement


class RoulettePrize(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name="roulette_prizes")

    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=50)  # FontAwesome icon class
    probability = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Probability percentage (min 1%)",
    )
    is_nothing_prize = models.BooleanField(default=False, help_text="Marks the 'no prize' option")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.etablissement.title} - {self.name} ({self.probability}%)"


class RouletteSpin(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name="roulette_spins")
    prize = models.ForeignKey(RoulettePrize, on_delete=models.CASCADE, related_name="spins")
    prize_code = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False, help_text="Whether code was redeemed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.etablissement.title} - {self.prize.name} - {self.prize_code}"


class RouletteAnalytics(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name="roulette_analytics")

    TYPE_CHOICES = [
        ("roulette_viewed", "Roulette Viewed"),
        ("roulette_spun", "Roulette Spun"),
        ("prize_won", "Prize Won"),
        ("no_prize", "No Prize"),
    ]

    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.etablissement.title} - {self.type}"
