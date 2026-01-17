from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserSession

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'company_name', 'is_verified')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'company_name', 'phone', 'tenant_id', 'is_verified')
        }),
    )

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'login_at', 'last_activity', 'is_active')
    list_filter = ('is_active', 'login_at')
    search_fields = ('user__username', 'ip_address')