import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


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


class GenerateTokenPlan(models.Model):
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='tokens',
        verbose_name=_("План")
    )
    token = models.CharField(max_length=255, unique=True, db_index=True, verbose_name=_("Токен"))
    is_activated = models.BooleanField(default=False, verbose_name=_("Активирован"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    
    class Meta:
        verbose_name = _("Токен плана")
        verbose_name_plural = _("02. Токены планов")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token для плана {self.plan.id}: {self.token[:20]}..."
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())
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
    token = models.ForeignKey(
        GenerateTokenPlan,
        on_delete=models.CASCADE,
        related_name='plan_users',
        verbose_name=_("Токен")
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
        verbose_name_plural = _("03. Участники планов")
        unique_together = ['plan', 'user', 'token']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.plan.name} ({self.get_status_display()})"
