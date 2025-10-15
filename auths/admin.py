from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import User, GoogleCredentials, Etablissement
from django.contrib import admin
from allauth.account.decorators import secure_admin_login

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'is_active')}),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')





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