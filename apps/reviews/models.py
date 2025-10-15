import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models




class Review(models.Model):
    etablissement = models.ForeignKey("auths.Etablissement", on_delete=models.CASCADE)

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review {self.rating}★ for {self.etablissement}"