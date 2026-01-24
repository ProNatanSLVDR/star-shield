
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from auths.models import Etablissement


class Review(models.Model):
    SOURCE_CHOICES = [
        ("internal", "Internal"),
        ("google", "Google"),
    ]

    etablissement = models.ForeignKey("auths.Etablissement", on_delete=models.CASCADE)

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="internal")

    google_review_id = models.CharField(max_length=255, blank=True, null=True)
    google_reviewer_data = models.JSONField(blank=True, null=True)

    writen_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.google_reviewer_data.get('displayName', 'Anonyme')} {self.rating}★ for {self.etablissement}"


class ReviewAnalytics(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE)

    TYPE_CHOICES = [
        ("feedback_viewed", "Feedback Viewed"),
        #
        # redirigé vers google
        ("feedback_external", "External Feedback"),
        #
        # feedback interne
        ("feedback_internal_viewed", "Internal Feedback Viewed"),
        ("feedback_internal_submitted", "Internal Feedback Submitted"),  # a soumis un feedback interne
    ]

    type = models.CharField(max_length=255, choices=TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.etablissement.title} - {self.type}"
