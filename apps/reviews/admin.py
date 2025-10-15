from django.contrib import admin

from .models import Etablissement, GoogleCredentials, Review

# Register your models here.
@admin.register(GoogleCredentials)
class GoogleCredentialsAdmin(admin.ModelAdmin):
    list_display = ("user", "is_valid", "created_at", "updated_at")
    search_fields = ("user__email",)
    list_filter = ("is_valid", "created_at")


@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ("name", "google_business_manager_account_id", "slug", "uuid", "review_threshold")
    search_fields = ("name", "google_business_manager_account_id", "slug", "uuid")
    list_filter = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "rating", "created_at")
    list_filter = ("rating", "created_at", "etablissement")
    search_fields = ("etablissement__name", "comment")