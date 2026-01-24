from django.contrib import admin
from .models import ChatRoom, ChatRoomGroup, ChatRoomMessage, Notification



class ChatRoomMessageInline(admin.TabularInline):
    model = ChatRoomMessage
    extra = 1
    fields = ['user', 'message', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'plan', 'user', 'channel_name', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['channel_name', 'plan__name', 'user__first_name', 'user__last_name', 'user__telegram_username']
    readonly_fields = ['channel_name', 'created_at', 'updated_at']
    inlines = [ChatRoomMessageInline]
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
