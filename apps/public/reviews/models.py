from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.private.auths.models import Etablissement


class Review(models.Model):
    SOURCE_CHOICES = [
        ("internal", "Internal"),
        ("google", "Google"),
    ]

    REPLY_TYPE_CHOICES = [
        ("ai", "AI"),
        ("google", "Google"),
    ]

    AI_RESPONSE_STATUS_CHOICES = [
        ("pending", "En attente"),
        ("approved", "Approuvé"),
        ("rejected", "Rejeté"),
        ("flagged", "Signalé"),
    ]

    etablissement = models.ForeignKey("auths.Etablissement", on_delete=models.CASCADE)

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], db_index=True)
    comment = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="internal")

    google_review_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    google_reviewer_data = models.JSONField(blank=True, null=True)

    # Reply tracking
    reply_comment = models.TextField(blank=True, null=True)
    reply_date = models.DateTimeField(blank=True, null=True, db_index=True)
    reply_type = models.CharField(max_length=10, choices=REPLY_TYPE_CHOICES, blank=True, null=True, db_index=True)

    # AI response workflow
    ai_response_status = models.CharField(
        max_length=10, choices=AI_RESPONSE_STATUS_CHOICES, blank=True, null=True, db_index=True
    )
    ai_draft_comment = models.TextField(blank=True, null=True)
    ai_flag_reason = models.CharField(max_length=255, blank=True, null=True)

    writen_at = models.DateTimeField(blank=True, null=True, db_index=True)
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
