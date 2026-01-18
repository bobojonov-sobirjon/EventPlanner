from rest_framework import serializers
from .models import CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя"""

    class Meta:
        model = CustomUser
        fields = ('id', 'first_name', 'last_name',
                  'phone', 'avatar', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TelegramAuthSerializer(serializers.Serializer):
    """Сериализатор для аутентификации через Telegram"""
    initData = serializers.CharField(
        required=True,
        help_text="Строка initData из Telegram Web App. Получается автоматически из window.Telegram.WebApp.initData"
    )
    invite_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Токен приглашения на план (опционально). Если передан, пользователь автоматически добавляется в план."
    )