from rest_framework import serializers
from .models import ChatRoom, ChatRoomGroup, ChatRoomMessage, Notification


class ChatRoomSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'plan', 'owner', 'channel_name', 
            'members_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'channel_name', 'created_at', 'updated_at')
    
    def get_plan(self, obj):
        from apps.v1.plans.serializers import PlanSerializer
        return PlanSerializer(obj.plan).data
    
    def get_owner(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data
    
    def get_members_count(self, obj):
        return obj.group_members.count()


class ChatRoomMessageSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    sender_type = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoomMessage
        fields = (
            'id', 'room', 'user', 'message', 'sender_type',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'room', 'user', 'sender_type', 'created_at', 'updated_at')
    
    def get_user(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data
    
    def get_sender_type(self, obj):
        # Joriy foydalanuvchi (request.user) yuborgan xabar → initiator (o'ng), boshqalar → receiver (chap)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated and obj.user_id == request.user.id:
            return 'initiator'
        return 'receiver'


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'plan', 'owner', 'channel_name', 
            'members', 'messages_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'channel_name', 'created_at', 'updated_at')
    
    def get_plan(self, obj):
        from apps.v1.plans.serializers import PlanSerializer
        return PlanSerializer(obj.plan).data
    
    def get_owner(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        return CustomUserSerializer(obj.user).data
    
    def get_members(self, obj):
        from apps.v1.accounts.serializers import CustomUserSerializer
        members = obj.group_members.all()
        return [CustomUserSerializer(member.user).data for member in members]
    
    def get_messages_count(self, obj):
        return obj.messages.count()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'title', 'message', 
            'data', 'is_read', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

