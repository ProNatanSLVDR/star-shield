from allauth.account.decorators import secure_admin_login
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from hijack.contrib.admin import HijackUserAdminMixin

from .models import Etablissement, GoogleCredentials, QRCode, RatingHistory, User, WeeklyPerformanceSummary

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)


@admin.register(User)
class UserAdmin(HijackUserAdminMixin, admin.ModelAdmin):
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
    list_display = ("user", "google_account_email", "is_valid", "has_invalid_grants", "created_at", "updated_at")
    search_fields = ("user__email", "google_account_email")
    list_filter = ("is_valid", "has_invalid_grants", "created_at")

    fieldsets = (
        (
            _("Account"),
            {"fields": ("user", "google_account_email")},
        ),
        (
            _("Status"),
            {"fields": ("is_valid", "has_invalid_grants")},
        ),
        (
            _("OAuth Tokens"),
            {
                "fields": ("token", "refresh_token", "token_uri", "client_id", "client_secret", "scopes"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")


class QRCodeInline(admin.TabularInline):
    model = QRCode
    extra = 0
    fields = ("name", "short_code", "routing", "locked", "created_at")
    readonly_fields = ("short_code", "created_at")
    show_change_link = True


class RatingHistoryInline(admin.TabularInline):
    model = RatingHistory
    extra = 0
    fields = ("rating", "total_reviews", "created_at")
    readonly_fields = ("rating", "total_reviews", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class WeeklyPerformanceSummaryInline(admin.TabularInline):
    model = WeeklyPerformanceSummary
    extra = 0
    fields = ("week_start_date", "short_summary", "created_at")
    readonly_fields = ("week_start_date", "short_summary", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "uuid", "active", "review_threshold", "roulette_enabled", "ai_responses_enabled")
    search_fields = ("title", "slug", "uuid")
    list_filter = ("active", "roulette_enabled", "ai_responses_enabled", "created_at", "updated_at")
    inlines = [QRCodeInline, RatingHistoryInline, WeeklyPerformanceSummaryInline]

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
            _("Review Filtering"),
            {"fields": ("review_filtering_enabled",)},
        ),
        (
            _("Roulette Settings"),
            {
                "fields": ("roulette_enabled", "roulette_spin_cooldown_days"),
                "classes": ("collapse",),
            },
        ),
        (
            _("AI Responses Settings"),
            {
                "fields": (
                    "ai_responses_enabled",
                    "ai_response_tone",
                    "ai_response_length",
                    "ai_response_language",
                ),
                "classes": ("collapse",),
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
    list_display = ("name", "short_code", "etablissement", "routing", "locked", "created_at")
    search_fields = ("name", "short_code", "etablissement__title")
    list_filter = ("routing", "locked", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "etablissement",
                    "name",
                    "short_code",
                    "routing",
                    "locked",
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
    readonly_fields = ("short_code", "created_at", "updated_at")


@admin.register(RatingHistory)
class RatingHistoryAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "rating", "total_reviews", "created_at")
    search_fields = ("etablissement__title",)
    list_filter = ("created_at",)

    fieldsets = (
        (
            _("Establishment"),
            {"fields": ("etablissement",)},
        ),
        (
            _("Rating Snapshot"),
            {"fields": ("rating", "total_reviews")},
        ),
        (
            _("Dates"),
            {"fields": ("created_at",)},
        ),
    )
    readonly_fields = ("etablissement", "rating", "total_reviews", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(WeeklyPerformanceSummary)
class WeeklyPerformanceSummaryAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "week_start_date", "short_summary", "created_at")
    search_fields = ("etablissement__title", "short_summary", "summary_text")
    list_filter = ("created_at",)
    date_hierarchy = "week_start_date"

    fieldsets = (
        (
            _("Establishment"),
            {"fields": ("etablissement",)},
        ),
        (
            _("Summary Content"),
            {"fields": ("week_start_date", "short_summary", "summary_text", "advice_text")},
        ),
        (
            _("Raw Data"),
            {
                "fields": ("metrics_data",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Dates"),
            {"fields": ("created_at",)},
        ),
    )
    readonly_fields = (
        "etablissement",
        "week_start_date",
        "short_summary",
        "summary_text",
        "advice_text",
        "metrics_data",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
