from rest_framework import serializers
from django.conf import settings
from .models import Plan, PlanUser, GenerateTokenPlan


class PlanSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    plan_users = serializers.SerializerMethodField()
    count_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Plan
        fields = (
            'id', 'emoji', 'name', 'location', 'lat', 'lng', 
            'datetime', 'user', 'user_plan_number', 'plan_users', 'count_user', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'user_plan_number', 'created_at', 'updated_at')
    
    def get_user(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data
    
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


class PlanUserSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanUser
        fields = (
            'id', 'plan', 'user', 'status', 
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'plan', 'user', 'status', 'created_at', 'updated_at')
    
    def get_user(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data
    
    def get_status(self, obj):
        """Возвращает русский перевод статуса вместо английского значения"""
        return obj.get_status_display()


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


class GenerateTokenPlanSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = GenerateTokenPlan
        fields = (
            'id', 'token', 'plan', 'created_by', 'expires_at', 
            'max_uses', 'current_uses', 'is_active', 'is_valid',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'token', 'created_at', 'updated_at')
    
    def get_plan(self, obj):
        from .serializers import PlanSerializer
        return PlanSerializer(obj.plan).data
    
    def get_created_by(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.created_by).data
    
    def get_is_valid(self, obj):
        """Token hali ham amal qiladimi"""
        return obj.is_valid()
