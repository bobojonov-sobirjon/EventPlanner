from django.urls import path
from .views import TelegramAuthAPIView, UserProfileAPIView

urlpatterns = [
    path('auth/telegram/', TelegramAuthAPIView.as_view(), name='telegram-auth'),
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
]