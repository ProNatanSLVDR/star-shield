from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("__str__", "etablissement", "rating", "source", "reply_type", "writen_at", "created_at")
    list_filter = ("rating", "source", "reply_type", "writen_at", "created_at", "etablissement")
    search_fields = ("etablissement__title", "comment", "google_reviewer_data__displayName")
    ordering = ("-writen_at", "-created_at")

    fieldsets = (
        (
            _("Review"),
            {"fields": ("etablissement", "rating", "comment", "source")},
        ),
        (
            _("Google Data"),
            {
                "fields": ("google_review_id", "google_reviewer_data"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Reply"),
            {
                "fields": (
                    "reply_comment",
                    "reply_date",
                    "reply_type",
                    "ai_response_status",
                    "ai_draft_comment",
                    "ai_flag_reason",
                )
            },
        ),
        (
            _("Dates"),
            {"fields": ("writen_at", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")
