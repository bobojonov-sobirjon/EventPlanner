from django.contrib import admin
from .models import Plan, PlanUser


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'emoji', 'location', 'datetime', 'user', 'user_plan_number', 'created_at']
    list_filter = ['datetime', 'created_at', 'user']
    search_fields = ['name', 'location', 'user__first_name', 'user__last_name', 'user__telegram_username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('emoji', 'name', 'location', 'lat', 'lng', 'datetime', 'user')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlanUser)
class PlanUserAdmin(admin.ModelAdmin):
    list_display = ['plan__name', 'plan__user_plan_number', 'user__first_name', 'user__last_name', 'user__telegram_username', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['plan__name', 'user__first_name', 'user__last_name', 'user__telegram_username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('plan', 'user', 'status')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
