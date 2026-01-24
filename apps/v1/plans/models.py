from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid
from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Plan(models.Model):
    emoji = models.CharField(max_length=10, verbose_name=_("Эмодзи"))
    name = models.CharField(max_length=255, verbose_name=_("Название"))
    location = models.CharField(max_length=255, verbose_name=_("Местоположение"))
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Широта"))
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Долгота"))
    datetime = models.DateTimeField(verbose_name=_("Дата и время"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='plans',
        verbose_name=_("Создатель")
    )
    user_plan_number = models.IntegerField(default=1, verbose_name=_("Номер плана пользователя"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
    class Meta:
        verbose_name = _("План")
        verbose_name_plural = _("01. Планы")
        ordering = ['-datetime', '-created_at']
    
    def __str__(self):
        return f"{self.emoji} {self.name} - {self.user}"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            user_plans_count = Plan.objects.filter(user=self.user).count()
            self.user_plan_number = user_plans_count + 1
        super().save(*args, **kwargs)


class PlanUser(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Ожидает ответа')
        APPROVED = 'approved', _('Принято')
        REJECTED = 'rejected', _('Отклонено')
        REMOVED_INTO_CHAT_GROUP = 'removed_into_chat_group', _('Удален из группы чата')
    
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='plan_users',
        verbose_name=_("План")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='plan_invitations',
        verbose_name=_("Пользователь")
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Статус")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
    class Meta:
        verbose_name = _("Участник плана")
        verbose_name_plural = _("02. Участники планов")
        unique_together = [['plan', 'user']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.plan.name} ({self.get_status_display()})"


class GenerateTokenPlan(models.Model):
    """
    Xavfsiz token modeli - har bir invite link uchun noyob token yaratadi.
    Token muddati, maksimal foydalanish soni va boshqa xavfsizlik sozlamalari bilan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_("ID"))
    token = models.CharField(max_length=100, unique=True, verbose_name=_("Токен"))
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='invite_tokens',
        verbose_name=_("План")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tokens',
        verbose_name=_("Создатель токена")
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Истекает"))
    max_uses = models.IntegerField(default=1, verbose_name=_("Максимальное количество использований"))
    current_uses = models.IntegerField(default=0, verbose_name=_("Текущее количество использований"))
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
    class Meta:
        verbose_name = _("Токен приглашения")
        verbose_name_plural = _("03. Токены приглашений")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['plan', 'is_active']),
        ]
    
    def __str__(self):
        return f"Token for {self.plan.name} (uses: {self.current_uses}/{self.max_uses})"
    
    def is_valid(self):
        """Token hali ham amal qiladimi tekshirish"""
        if not self.is_active:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        if self.current_uses >= self.max_uses:
            return False
        
        return True
    
    def can_be_used(self):
        """Token hozir ishlatilishi mumkinmi"""
        return self.is_valid()
    
    def use_token(self):
        """Tokenni ishlatish - current_uses ni oshiradi"""
        if not self.can_be_used():
            return False
        
        self.current_uses += 1
        
        # Agar max_uses ga yetgan bo'lsa, avtomatik deaktivatsiya qilish
        if self.current_uses >= self.max_uses:
            self.is_active = False
            logger.info(
                f"Token {self.token} (Plan: {self.plan.id}) avtomatik deaktivatsiya qilindi. "
                f"Sabab: Maksimal foydalanish soniga yetdi ({self.current_uses}/{self.max_uses})"
            )
        
        self.save(update_fields=['current_uses', 'is_active', 'updated_at'])
        return True
    
    def save(self, *args, **kwargs):
        # Agar token yaratilmagan bo'lsa, UUID asosida yaratamiz
        if not self.token:
            self.token = str(self.id).replace('-', '')[:32]
        
        # Avtomatik deaktivatsiya tekshiruvi
        was_active = self.is_active if self.pk else True
        
        # Agar muddati tugagan bo'lsa, deaktivatsiya qilish
        if self.is_active and self.expires_at and timezone.now() > self.expires_at:
            self.is_active = False
            logger.info(
                f"Token {self.token} (Plan: {self.plan.id}) avtomatik deaktivatsiya qilindi. "
                f"Sabab: Muddati tugadi. Expires at: {self.expires_at}"
            )
        
        # Agar max_uses ga yetgan bo'lsa, deaktivatsiya qilish
        if self.is_active and self.current_uses >= self.max_uses:
            self.is_active = False
            logger.info(
                f"Token {self.token} (Plan: {self.plan.id}) avtomatik deaktivatsiya qilindi. "
                f"Sabab: Maksimal foydalanish soniga yetdi ({self.current_uses}/{self.max_uses})"
            )
        
        super().save(*args, **kwargs)
        
        # Agar yangi deaktivatsiya qilingan bo'lsa, log qo'shish
        if was_active and not self.is_active and self.pk:
            logger.warning(
                f"Token {self.token} (Plan: {self.plan.id}) deaktivatsiya qilindi. "
                f"Current uses: {self.current_uses}/{self.max_uses}, "
                f"Expires at: {self.expires_at}, "
                f"Is active: {self.is_active}"
            )
