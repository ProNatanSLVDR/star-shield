from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import RoulettePrize, RouletteSpin


class RouletteSpinInline(admin.TabularInline):
    model = RouletteSpin
    extra = 0
    fields = ("prize_code", "is_used", "created_at")
    readonly_fields = ("prize_code", "is_used", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RoulettePrize)
class RoulettePrizeAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "name", "icon", "probability", "is_nothing_prize", "created_at")
    list_filter = ("etablissement", "is_nothing_prize", "created_at")
    search_fields = ("name", "etablissement__title")
    ordering = ("etablissement", "created_at")
    inlines = [RouletteSpinInline]

    fieldsets = (
        (
            _("Prize Configuration"),
            {"fields": ("etablissement", "name", "icon", "probability", "is_nothing_prize")},
        ),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(RouletteSpin)
class RouletteSpinAdmin(admin.ModelAdmin):
    list_display = ("etablissement", "prize", "prize_code", "is_used", "created_at")
    list_filter = ("etablissement", "is_used", "created_at")
    search_fields = ("prize_code", "etablissement__title", "prize__name")
    readonly_fields = ("etablissement", "prize", "prize_code", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            _("Spin Details"),
            {"fields": ("etablissement", "prize", "prize_code")},
        ),
        (
            _("Status"),
            {"fields": ("is_used",)},
        ),
        (
            _("Dates"),
            {"fields": ("created_at",)},
        ),
    )

    def has_add_permission(self, request):
        return False
