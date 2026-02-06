from django.db import models


class StripeSubscription(models.Model):
    etablissement = models.ForeignKey(
        "auths.Etablissement", on_delete=models.CASCADE, related_name="stripe_subscription"
    )
    subscription_id = models.CharField(max_length=255, unique=True)

    status = models.CharField(max_length=50)
    price_id = models.CharField(max_length=255, blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.etablissement} - {self.status}"
