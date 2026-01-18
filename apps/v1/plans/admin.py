from django.contrib import admin
from .models import Plan, GenerateTokenPlan, PlanUser


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


@admin.register(GenerateTokenPlan)
class GenerateTokenPlanAdmin(admin.ModelAdmin):
    list_display = ['plan__name', 'plan__user_plan_number', 'token', 'is_activated', 'created_at']
    list_filter = ['is_activated', 'created_at']
    search_fields = ['token', 'plan__name']
    readonly_fields = ['token', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('plan', 'token', 'is_activated')
        }),
        ('Системная информация', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlanUser)
class PlanUserAdmin(admin.ModelAdmin):
    list_display = ['plan__name', 'plan__user_plan_number', 'user__first_name', 'user__last_name', 'user__telegram_username', 'token__token', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['plan__name', 'user__first_name', 'user__last_name', 'user__telegram_username', 'token__token']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('plan', 'token', 'user', 'status')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
