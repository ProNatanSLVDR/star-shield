from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "rating", "created_at")
    list_filter = ("rating", "created_at", "etablissement")
    search_fields = ("etablissement__name", "comment")