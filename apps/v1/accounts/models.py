from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    tg_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name="Telegram ID", db_index=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name="Telegram ID (legacy)")
    telegram_username = models.CharField(max_length=255, null=True, blank=True, verbose_name="Имя пользователя Telegram")
    first_name = models.CharField(max_length=30, null=True, blank=True, verbose_name="Имя")
    last_name = models.CharField(max_length=30, null=True, blank=True, verbose_name="Фамилия")
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Телефон")
    avatar = models.URLField(null=True, blank=True, verbose_name="Аватар")
    photo_url = models.URLField(null=True, blank=True, verbose_name="URL фотографии (legacy)")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip() or f"({self.username})"
        return self.username or f"tg_{self.tg_id}" or str(self.id)
