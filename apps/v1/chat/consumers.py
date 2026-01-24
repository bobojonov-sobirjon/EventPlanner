import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatRoomGroup, ChatRoomMessage, Notification

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        is_member = await self.check_room_membership(self.room_id, self.user)
        if not is_member:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat room'
        }, ensure_ascii=False))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            
            if not message:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Сообщение не может быть пустым'
                }, ensure_ascii=False))
                return
            
            room = await self.get_room(self.room_id)
            if not room:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Комната не найдена'
                }, ensure_ascii=False))
                return
            
            chat_message = await self.save_message(room, self.user, message)
            print(f"[DEBUG] Chat message saved - ID: {chat_message.id}, Room ID: {room.id}, User ID: {self.user.id}")
            
            is_room_owner = await self.check_room_owner(room, self.user)
            sender_type = 'initiator' if is_room_owner else 'receiver'
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': chat_message.id,
                        'user': {
                            'id': self.user.id,
                            'first_name': self.user.first_name or '',
                            'last_name': self.user.last_name or '',
                            'avatar': self.user.avatar or '',
                        },
                        'message': chat_message.message,
                        'sender_type': sender_type,
                        'created_at': chat_message.created_at.isoformat(),
                    }
                }
            )
            print(f"[DEBUG] Chat message broadcasted to group: {self.room_group_name}")
            
            print(f"[DEBUG] Calling send_notifications...")
            await self.send_notifications(room, self.user, chat_message)
            print(f"[DEBUG] send_notifications completed")
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Неверный формат JSON'
            }, ensure_ascii=False))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Ошибка: {str(e)}'
            }, ensure_ascii=False))
    
    async def chat_message(self, event):
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }, ensure_ascii=False))
    
    @database_sync_to_async
    def check_room_membership(self, room_id, user):
        try:
            room = ChatRoom.objects.get(id=room_id)
            return ChatRoomGroup.objects.filter(room=room, user=user).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_room(self, room_id):
        try:
            return ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def check_room_owner(self, room, user):
        return room.user == user
    
    @database_sync_to_async
    def save_message(self, room, user, message):
        return ChatRoomMessage.objects.create(
            room=room,
            user=user,
            message=message
        )
    
    async def send_notifications(self, room, sender, chat_message):
        try:
            print(f"[DEBUG] send_notifications called - Room ID: {room.id}, Sender ID: {sender.id}")
            members = await self.get_room_members(room)
            print(f"[DEBUG] Found {len(members)} members in room")
            plan_name = await self.get_plan_name(room)
            plan_id = await self.get_plan_id(room)
            print(f"[DEBUG] Plan: {plan_name} (ID: {plan_id})")
            
            for member in members:
                print(f"[DEBUG] Processing member ID: {member.id}, Sender ID: {sender.id}")
                if member.id != sender.id:
                    print(f"[DEBUG] Creating notification for member ID: {member.id}")
                    notification = await self.create_notification(
                        user=member,
                        notification_type='chat_message',
                        title=f'Новое сообщение в плане "{plan_name}"',
                        message=chat_message.message,
                        data={
                            'room_id': room.id,
                            'message_id': chat_message.id,
                            'sender_id': sender.id,
                            'plan_id': plan_id
                        }
                    )
                    print(f"[DEBUG] Notification created with ID: {notification.id} for user ID: {member.id}")
                    
                    notification_data = await self.get_notification_data(notification)
                    print(f"[DEBUG] Notification data prepared: {notification_data}")
                    
                    group_name = f'notifications_{member.id}'
                    print(f"[DEBUG] Sending notification to group: {group_name}")
                    await self.channel_layer.group_send(
                        group_name,
                        {
                            'type': 'notification',
                            'notification': notification_data
                        }
                    )
                    print(f"[DEBUG] Notification sent to group: {group_name}")
                else:
                    print(f"[DEBUG] Skipping sender (member ID == sender ID)")
        except Exception as e:
            # Log error but don't crash chat functionality
            import traceback
            print(f"[ERROR] Error sending notifications: {str(e)}")
            print(traceback.format_exc())
    
    @database_sync_to_async
    def get_room_members(self, room):
        members = ChatRoomGroup.objects.filter(room=room).select_related('user')
        return [member.user for member in members]
    
    @database_sync_to_async
    def get_plan_name(self, room):
        return room.plan.name
    
    @database_sync_to_async
    def get_plan_id(self, room):
        return room.plan.id
    
    @database_sync_to_async
    def create_notification(self, user, notification_type, title, message, data):
        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data
        )
    
    @database_sync_to_async
    def get_notification_data(self, notification):
        # Refresh from database to ensure all fields are loaded
        notification.refresh_from_db()
        return {
            'id': notification.id,
            'notification_type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'data': notification.data if isinstance(notification.data, dict) else {},
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
        }


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        print(f"[DEBUG] NotificationConsumer.connect - User ID: {self.user.id}, Is Anonymous: {self.user.is_anonymous}")
        
        if self.user.is_anonymous:
            print(f"[DEBUG] User is anonymous, closing connection")
            await self.close()
            return
        
        self.notification_group_name = f'notifications_{self.user.id}'
        print(f"[DEBUG] Notification group name: {self.notification_group_name}")
        print(f"[DEBUG] Channel name: {self.channel_name}")
        
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        print(f"[DEBUG] Added to notification group: {self.notification_group_name}")
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notifications'
        }, ensure_ascii=False))
        print(f"[DEBUG] NotificationConsumer connection established for user ID: {self.user.id}")
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )
    
    async def notification(self, event):
        try:
            print(f"[DEBUG] NotificationConsumer.notification called - User ID: {self.user.id}")
            print(f"[DEBUG] Event received: {event}")
            notification = event['notification']
            print(f"[DEBUG] Notification data: {notification}")
            
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'notification': notification
            }, ensure_ascii=False))
            print(f"[DEBUG] Notification sent to WebSocket for user ID: {self.user.id}")
        except Exception as e:
            # Log error but don't crash
            import traceback
            print(f"[ERROR] Error sending notification: {str(e)}")
            print(traceback.format_exc())