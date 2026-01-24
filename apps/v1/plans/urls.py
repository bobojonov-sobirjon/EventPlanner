from django.urls import path
from .views import (
    PlanCreateAPIView,
    PlanListAPIView,
    PlanDetailAPIView,
    PlanGenerateTokenAPIView,
    PlanUpdateAPIView,
    PlanApproveAPIView,
    PlanRejectAPIView,
    PlanDeleteAPIView,
    FriendsListAPIView,
    PlanFriendsAPIView,
    PlanFriendsBulkTokenAPIView,
    PlanTokenDetailAPIView
)

urlpatterns = [
    path('create/', PlanCreateAPIView.as_view(), name='plan-create'),
    path('list/', PlanListAPIView.as_view(), name='plan-list'),
    path('friends/', PlanFriendsAPIView.as_view(), name='plan-friends'),
    path('<int:plan_id>/', PlanDetailAPIView.as_view(), name='plan-detail'),
    path('<int:plan_id>/generate-token/', PlanGenerateTokenAPIView.as_view(), name='plan-generate-token'),
    path('<int:plan_id>/generate-token/friends/', PlanFriendsBulkTokenAPIView.as_view(), name='plan-generate-token-friends'),
    path('<int:plan_id>/update/', PlanUpdateAPIView.as_view(), name='plan-update'),
    path('approve/', PlanApproveAPIView.as_view(), name='plan-approve'),
    path('reject/', PlanRejectAPIView.as_view(), name='plan-reject'),
    path('<int:plan_id>/delete/', PlanDeleteAPIView.as_view(), name='plan-delete'),
    path('token/<str:token>/', PlanTokenDetailAPIView.as_view(), name='plan-token-detail'),
]
