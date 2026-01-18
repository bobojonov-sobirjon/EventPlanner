from django.urls import path
from .views import (
    MyChatRoomsAPIView,
    ChatRoomDetailAPIView,
    ChatRoomMessagesAPIView,
    NotificationListAPIView,
    NotificationDetailAPIView
)

urlpatterns = [
    path('rooms/', MyChatRoomsAPIView.as_view(), name='my-chat-rooms'),
    path('rooms/<int:room_id>/', ChatRoomDetailAPIView.as_view(), name='chat-room-detail'),
    path('rooms/<int:room_id>/messages/', ChatRoomMessagesAPIView.as_view(), name='chat-room-messages'),
    path('notifications/', NotificationListAPIView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/', NotificationDetailAPIView.as_view(), name='notification-detail'),
]
