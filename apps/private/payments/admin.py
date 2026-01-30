from django.contrib import admin

from .models import StripeSubscription


@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "etablissement",
        "status",
        "price_id",
        "cancel_at_period_end",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
