import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models




class Review(models.Model):
    SOURCE_CHOICES = [
        ('internal', 'Internal'),
        ('google', 'Google'),
    ]
    
    etablissement = models.ForeignKey("auths.Etablissement", on_delete=models.CASCADE)

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='internal')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review {self.rating}★ for {self.etablissement}"