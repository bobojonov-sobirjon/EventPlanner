from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Административная конфигурация для CustomUser"""
    list_display = ['tg_id', 'telegram_username', 'first_name', 'last_name', 'phone', 'email', 'is_active', 'is_staff', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'created_at']
    search_fields = ['tg_id', 'telegram_id', 'telegram_username', 'username', 'email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'date_joined']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Данные Telegram', {
            'fields': ('tg_id', 'telegram_id', 'telegram_username', 'first_name', 'last_name', 'phone', 'avatar')
        }),
        ('Личные данные', {'fields': ('email',)}),
        ('Разрешения', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'tg_id', 'telegram_username'),
        }),
    )
