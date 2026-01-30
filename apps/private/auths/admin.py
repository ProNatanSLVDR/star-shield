from allauth.account.decorators import secure_admin_login
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Etablissement, GoogleCredentials, QRCode, RatingHistory, User

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "onboarding_completed",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "onboarding_completed")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "profile_picture")},
        ),
        (_("Permissions"), {"fields": ("is_staff", "is_superuser", "is_active")}),
        (_("Settings"), {"fields": ("onboarding_completed", "stripe_customer_id")}),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(GoogleCredentials)
class GoogleCredentialsAdmin(admin.ModelAdmin):
    list_display = ("user", "is_valid", "created_at", "updated_at")
    search_fields = ("user__email",)
    list_filter = ("is_valid", "created_at")


@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "uuid", "active", "review_threshold")
    search_fields = ("title", "slug", "uuid")
    list_filter = ("active", "created_at", "updated_at")

    fieldsets = (
        (
            _("Important/Core Fields"),
            {
                "fields": (
                    "google_credential",
                    "location_id",
                    "account_id",
                    "active",
                    "uuid",
                    "slug",
                )
            },
        ),
        (
            _("General Settings"),
            {
                "fields": (
                    "title",
                    "review_threshold",
                    "target_rating",
                )
            },
        ),
        (
            _("Personalisation Settings"),
            {
                "fields": (
                    "review_accent_color",
                    "review_show_etablissement_pill",
                    "review_page_label",
                    "review_page_text",
                )
            },
        ),
        (
            _("URLs"),
            {
                "fields": (
                    "website_uri",
                    "maps_uri",
                    "new_reviews_uri",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "last_reviews_update",
                )
            },
        ),
    )
    readonly_fields = ("uuid", "created_at", "updated_at", "last_reviews_update")


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ("name", "etablissement", "routing", "created_at")
    search_fields = ("name", "etablissement__title")
    list_filter = ("routing", "created_at")
    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "etablissement",
                    "name",
                    "routing",
                )
            },
        ),
        (
            _("QR Code Customization"),
            {
                "fields": (
                    "qr_fill_color",
                    "qr_fill_color_secondary",
                    "qr_background_color",
                    "qr_style",
                    "qr_color_mask",
                    "qr_logo",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(RatingHistory)
class RatingHistoryAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "rating", "total_reviews", "created_at")
    search_fields = ("etablissement__title",)
    list_filter = ("created_at",)
