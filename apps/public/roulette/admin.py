from django.contrib import admin

from .models import RouletteAnalytics, RoulettePrize, RouletteSpin


@admin.register(RoulettePrize)
class RoulettePrizeAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "name", "icon", "probability", "is_nothing_prize", "created_at")
    list_filter = ("etablissement", "is_nothing_prize", "created_at")
    search_fields = ("name", "etablissement__title")
    ordering = ("etablissement", "created_at")


@admin.register(RouletteSpin)
class RouletteSpinAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "prize", "prize_code", "is_used", "created_at")
    list_filter = ("etablissement", "is_used", "created_at")
    search_fields = ("prize_code", "etablissement__title", "prize__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(RouletteAnalytics)
class RouletteAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "type", "created_at")
    list_filter = ("type", "etablissement", "created_at")
    search_fields = ("etablissement__title",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
