from rest_framework import serializers
from django.conf import settings
from .models import Plan, GenerateTokenPlan, PlanUser


class PlanSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    tokens = serializers.SerializerMethodField()
    plan_users = serializers.SerializerMethodField()
    count_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Plan
        fields = (
            'id', 'emoji', 'name', 'location', 'lat', 'lng', 
            'datetime', 'user', 'user_plan_number', 'tokens', 'plan_users', 'count_user', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'user_plan_number', 'created_at', 'updated_at')
    
    def get_user(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data
    
    def get_tokens(self, obj):
        return GenerateTokenPlanSerializer(obj.tokens.all(), many=True).data
    
    def get_plan_users(self, obj):
        return PlanUserSerializer(obj.plan_users.all(), many=True).data
    
    def get_count_user(self, obj):
        return obj.plan_users.filter(status=PlanUser.Status.APPROVED).count()


class PlanCreateSerializer(serializers.Serializer):
    emoji = serializers.CharField(
        required=True,
        max_length=10,
        help_text="Эмодзи для плана (например: 🍕)"
    )
    name = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Название плана"
    )
    location = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Местоположение (адрес)"
    )
    lat = serializers.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        help_text="Широта (latitude)"
    )
    lng = serializers.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        help_text="Долгота (longitude)"
    )
    datetime = serializers.DateTimeField(
        required=True,
        help_text="Дата и время встречи (формат: YYYY-MM-DDTHH:MM:SS)"
    )


class GenerateTokenPlanSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    msg = serializers.SerializerMethodField()
    
    class Meta:
        model = GenerateTokenPlan
        fields = ('id', 'token', 'link', 'msg')
        read_only_fields = ('id', 'token', 'link', 'msg')
    
    def get_link(self, obj):
        bot_name = getattr(settings, 'BOT_NAME', None)
        if bot_name:
            return f"https://t.me/{bot_name}?start={obj.token}"
        return None
    
    def get_msg(self, obj):
        plan = obj.plan
        creator = plan.user
        
        creator_name = creator.first_name or creator.last_name or creator.username or "Пользователь"
        if creator.first_name and creator.last_name:
            creator_name = f"{creator.first_name} {creator.last_name}".strip()
        elif creator.first_name:
            creator_name = creator.first_name
        elif creator.last_name:
            creator_name = creator.last_name
        
        plan_name = plan.name
        plan_datetime = plan.datetime.strftime("%d.%m.%Y %H:%M")
        
        bot_name = getattr(settings, 'BOT_NAME', 'your_bot')
        link = f"https://t.me/{bot_name}?start={obj.token}"
        
        msg = f"{creator_name} приглашает вас на план «{plan_name}» на {plan_datetime}. Присоединяйтесь: {link}"
        
        return msg


class PlanUserSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    token = GenerateTokenPlanSerializer(read_only=True)
    
    class Meta:
        model = PlanUser
        fields = (
            'id', 'plan', 'token', 'user', 'status', 
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'plan', 'token', 'user', 'created_at', 'updated_at')
    
    def get_user(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data


class PlanUpdateSerializer(serializers.Serializer):
    emoji = serializers.CharField(
        required=False,
        max_length=10,
        help_text="Эмодзи для плана"
    )
    name = serializers.CharField(
        required=False,
        max_length=255,
        help_text="Название плана"
    )
    location = serializers.CharField(
        required=False,
        max_length=255,
        help_text="Местоположение (адрес)"
    )
    lat = serializers.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        help_text="Широта (latitude)"
    )
    lng = serializers.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        help_text="Долгота (longitude)"
    )
    datetime = serializers.DateTimeField(
        required=False,
        help_text="Дата и время встречи (формат: YYYY-MM-DDTHH:MM:SS)"
    )


class PlanApproveRejectSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(
        required=True,
        help_text="ID плана"
    )
    token_id = serializers.CharField(
        required=True,
        help_text="ID токена (UUID string или integer ID)"
    )


class FriendSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    plan_ids = serializers.SerializerMethodField()
    plans_count = serializers.SerializerMethodField()
    
    def get_user(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        if isinstance(obj, dict):
            return CustomUserSerializer(obj['user']).data
        return CustomUserSerializer(obj).data
    
    def get_plan_ids(self, obj):
        if isinstance(obj, dict):
            return obj.get('plan_ids', [])
        return []
    
    def get_plans_count(self, obj):
        if isinstance(obj, dict):
            return len(obj.get('plan_ids', []))
        return 0


class PlanFriendsBulkTokenSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="Список ID пользователей для генерации токенов"
    )
