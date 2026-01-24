from django.urls import path
from .views import (
    MyChatRoomsAPIView,
    ChatRoomDetailAPIView,
    ChatRoomMessagesAPIView,
    NotificationListAPIView,
    NotificationDetailAPIView,
    RemoveUserFromRoomAPIView
)

urlpatterns = [
    path('rooms/', MyChatRoomsAPIView.as_view(), name='my-chat-rooms'),
    path('rooms/<int:room_id>/', ChatRoomDetailAPIView.as_view(), name='chat-room-detail'),
    path('rooms/<int:room_id>/messages/', ChatRoomMessagesAPIView.as_view(), name='chat-room-messages'),
    path(
        "rooms/<int:room_id>/remove-user/<int:user_id>/",
        RemoveUserFromRoomAPIView.as_view(),
        name="remove-user-from-room"
    ),
    path('notifications/', NotificationListAPIView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/', NotificationDetailAPIView.as_view(), name='notification-detail'),
]
