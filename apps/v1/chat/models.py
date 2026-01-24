import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ChatRoom(models.Model):
    plan = models.OneToOneField(
        'plans.Plan',
        on_delete=models.CASCADE,
        related_name='chat_room',
        verbose_name=_("План")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_chat_rooms',
        verbose_name=_("Владелец")
    )
    channel_name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name=_("Название канала")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
    class Meta:
        verbose_name = _("Чат комната")
        verbose_name_plural = _("01. Чат комнаты")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.id} - Чат для плана {self.plan.id} - {self.plan.name} - {self.channel_name}"
    
    def save(self, *args, **kwargs):
        if not self.channel_name:
            self.channel_name = f"plan_{self.plan_id}_{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)


class ChatRoomGroup(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_room_groups',
        verbose_name=_("Пользователь")
    )
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='group_members',
        verbose_name=_("Комната")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    
    class Meta:
        verbose_name = _("Участник чат комнаты")
        verbose_name_plural = _("02. Участники чат комнат")
        unique_together = ['user', 'room']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.room.channel_name}"


class ChatRoomMessage(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_("Комната")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name=_("Пользователь")
    )
    message = models.TextField(verbose_name=_("Сообщение"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
    class Meta:
        verbose_name = _("Сообщение чата")
        verbose_name_plural = _("Сообщения чата")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.message[:50]}..."


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("Пользователь")
    )
    notification_type = models.CharField(
        max_length=50,
        verbose_name=_("Тип уведомления")
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Заголовок")
    )
    message = models.TextField(verbose_name=_("Сообщение"))
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Дополнительные данные")
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_("Прочитано")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
    class Meta:
        verbose_name = _("Уведомление")
        verbose_name_plural = _("Уведомления")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.title}"
