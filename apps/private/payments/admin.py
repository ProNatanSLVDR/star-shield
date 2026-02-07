from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import StripeSubscription


@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "etablissement",
        "subscription_id",
        "status",
        "price_id",
        "cancel_at_period_end",
        "created_at",
    )
    list_filter = ("status", "cancel_at_period_end", "created_at")
    search_fields = ("subscription_id", "price_id", "etablissement__title")
    ordering = ("-created_at",)

    fieldsets = (
        (
            _("Subscription"),
            {"fields": ("etablissement", "subscription_id")},
        ),
        (
            _("Plan Details"),
            {"fields": ("status", "price_id", "cancel_at_period_end")},
        ),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at")},
        ),
    )
    readonly_fields = (
        "subscription_id",
        "created_at",
        "updated_at",
    )
