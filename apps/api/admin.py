from django.contrib import admin

from .models import ApiToken


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'prefix', 'is_active', 'last_used_at', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_used_at')
    search_fields = ('name', 'prefix', 'user__email', 'user__username', 'user__display_name')
    readonly_fields = ('prefix', 'key_hash', 'last_used_at', 'created_at', 'updated_at')
