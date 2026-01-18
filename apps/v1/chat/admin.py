from django.contrib import admin
from .models import ChatRoom, ChatRoomGroup, ChatRoomMessage, Notification


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'plan', 'user', 'channel_name', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['channel_name', 'plan__name', 'user__first_name', 'user__last_name', 'user__telegram_username']
    readonly_fields = ['channel_name', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('plan', 'user', 'channel_name')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChatRoomGroup)
class ChatRoomGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'room', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__telegram_username', 'room__channel_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'room')
        }),
        ('Системная информация', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChatRoomMessage)
class ChatRoomMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'user', 'message', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['message', 'user__first_name', 'user__last_name', 'room__channel_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('room', 'user', 'message')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type', 'created_at']
    search_fields = ['title', 'message', 'user__first_name', 'user__last_name', 'user__telegram_username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'notification_type', 'title', 'message', 'data', 'is_read')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
