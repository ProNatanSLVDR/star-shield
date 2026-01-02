from django.contrib import admin
from .models import StripeSubscription


@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user_email",
        "user_name",
        "status",
        "current_period_end",
        "payment_method_display",
        "cancel_at_period_end",
        "created_at",
        "updated_at",
    )
    
    list_filter = (
        "status",
        "cancel_at_period_end",
        "payment_method_brand",
        "created_at",
    )
    
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "subscription_id",
        "user__stripe_customer_id",
    )
    
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    
    raw_id_fields = ("user",)
    
    date_hierarchy = "created_at"
    
    list_per_page = 50
    
    fieldsets = (
        ("User Information", {
            "fields": ("user",)
        }),
        ("Subscription Details", {
            "fields": (
                "subscription_id",
                "status",
                "price_id",
                "current_period_start",
                "current_period_end",
                "cancel_at_period_end",
            )
        }),
        ("Payment Method", {
            "fields": (
                "payment_method_brand",
                "payment_method_last4",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else "-"
    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"
    
    def user_name(self, obj):
        if obj.user:
            name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return name if name else obj.user.email
        return "-"
    user_name.short_description = "User Name"
    user_name.admin_order_field = "user__first_name"
    
    def payment_method_display(self, obj):
        if obj.payment_method_brand and obj.payment_method_last4:
            return f"{obj.payment_method_brand.upper()} •••• {obj.payment_method_last4}"
        return "-"
    payment_method_display.short_description = "Payment Method"
