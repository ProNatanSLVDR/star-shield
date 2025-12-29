from django.db import models
from django.conf import settings

class StripeSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stripe_subscription")
    subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50)
    price_id = models.CharField(max_length=255, blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    
    # Store payment method details denormalized for easy access
    payment_method_brand = models.CharField(max_length=50, blank=True, null=True)
    payment_method_last4 = models.CharField(max_length=4, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.status}"
