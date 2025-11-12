from django.contrib import admin

from .models import Review, ReviewAnalytics


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "rating", "created_at")
    list_filter = ("rating", "created_at", "etablissement")
    search_fields = ("etablissement__name", "comment")


@admin.register(ReviewAnalytics)
class ReviewAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "type", "created_at")
    list_filter = ("type", "created_at", "etablissement")
    search_fields = ("etablissement__name", "type")
