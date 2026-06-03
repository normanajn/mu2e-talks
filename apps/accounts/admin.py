from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Institution, InstitutionAlias, User, UserAlias


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'collaboration_number', 'collaboration_code', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('name',)
    ordering = ('sort_order', 'name')


@admin.register(InstitutionAlias)
class InstitutionAliasAdmin(admin.ModelAdmin):
    list_display = ('alias', 'institution', 'is_active', 'updated_at')
    list_filter = ('is_active', 'institution')
    search_fields = ('alias', 'institution__name')
    ordering = ('alias',)


@admin.register(UserAlias)
class UserAliasAdmin(admin.ModelAdmin):
    list_display = ('full_name_alias', 'first_name_alias', 'last_name_alias', 'user', 'institution', 'is_active')
    list_filter = ('is_active', 'institution')
    search_fields = ('full_name_alias', 'first_name_alias', 'last_name_alias', 'user__display_name', 'user__email')
    ordering = ('last_name_alias', 'first_name_alias', 'full_name_alias')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'contact_email', 'display_name', 'institution', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'institution', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Mu2e Info', {'fields': (
            'role', 'display_name', 'institution', 'contact_email',
            'collaboration_member_number', 'collaboration_start_date',
            'collaboration_position', 'collaboration_international',
            'office_phone', 'mobile_phone', 'other_phone', 'collaboration_status',
            'orcid', 'inspire_id', 'fnal_username', 'github_username',
            'collaboration_flag', 'minority_serving', 'roster_comments',
            'is_collaboration_member', 'roster_merge_completed',
        )}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Mu2e Info', {'fields': ('role', 'display_name', 'institution')}),
    )
    search_fields = ('email', 'contact_email', 'username', 'display_name')
    ordering = ('email',)
