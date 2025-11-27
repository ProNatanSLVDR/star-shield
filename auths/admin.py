from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import User, GoogleCredentials, Etablissement, RatingHistory
from django.contrib import admin
from allauth.account.decorators import secure_admin_login

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
        (_("Settings"), {"fields": ("onboarding_completed",)}),
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
    list_display = ("title", "slug", "uuid", "review_threshold")
    search_fields = ("title", "slug", "uuid")
    list_filter = ("created_at", "updated_at")


@admin.register(RatingHistory)
class RatingHistoryAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "rating", "total_reviews", "created_at")
    search_fields = ("etablissement__title",)
    list_filter = ("created_at",)
