from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import ChatRoom, ChatRoomGroup, ChatRoomMessage, Notification
from apps.v1.plans.models import PlanUser
from .serializers import (
    ChatRoomSerializer, ChatRoomDetailSerializer, ChatRoomMessageSerializer,
    NotificationSerializer
)


@extend_schema(
    tags=['Chat'],
    summary="Мои чат комнаты",
    description="""
    Получение списка всех чат комнат текущего аутентифицированного пользователя.
    
    Возвращает комнаты, в которых пользователь является участником (ChatRoomGroup).
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Пример ответа:**
    ```json
    {
        "rooms": [
            {
                "id": 1,
                "plan": {
                    "id": 1,
                    "emoji": "🍕",
                    "name": "Пицца с Аней",
                    ...
                },
                "owner": {
                    "id": 1,
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    ...
                },
                "channel_name": "plan_1_abc123def456",
                "members_count": 3,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z"
            }
        ]
    }
    ```
    """,
    responses={
        200: {
            'description': 'Список чат комнат успешно получен.',
            'content': {
                'application/json': {
                    'example': {
                        'rooms': []
                    }
                }
            }
        },
        401: {
            'description': 'Токен не предоставлен или недействителен.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Учетные данные не были предоставлены.'
                    }
                }
            }
        }
    }
)
class MyChatRoomsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        user_rooms = ChatRoom.objects.filter(
            group_members__user=user
        ).distinct().order_by('-created_at')
        
        serializer = ChatRoomSerializer(user_rooms, many=True)
        
        return Response({
            'rooms': serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Chat'],
    summary="Детали чат комнаты",
    description="""
    Получение детальной информации о чат комнате по её ID.
    
    Возвращает информацию о комнате, плане, владельце, участниках и количестве сообщений.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Параметры:**
    - `room_id` (path parameter) - ID чат комнаты
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "plan": {
            "id": 1,
            "emoji": "🍕",
            "name": "Пицца с Аней",
            ...
        },
        "owner": {
            "id": 1,
            "first_name": "Иван",
            "last_name": "Иванов",
            ...
        },
        "channel_name": "plan_1_abc123def456",
        "members": [
            {
                "id": 1,
                "first_name": "Иван",
                "last_name": "Иванов",
                ...
            },
            {
                "id": 2,
                "first_name": "Аня",
                "last_name": "Иванова",
                ...
            }
        ],
        "messages_count": 15,
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z"
    }
    ```
    """,
    responses={
        200: OpenApiResponse(
            response=ChatRoomDetailSerializer,
            description='Детали чат комнаты успешно получены.'
        ),
        403: {
            'description': 'Пользователь не является участником этой комнаты.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы не являетесь участником этой чат комнаты.'
                    }
                }
            }
        },
        404: {
            'description': 'Чат комната не найдена.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Не найдено.'
                    }
                }
            }
        },
        401: {
            'description': 'Токен не предоставлен или недействителен.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Учетные данные не были предоставлены.'
                    }
                }
            }
        }
    }
)
class ChatRoomDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        
        user = request.user
        if not ChatRoomGroup.objects.filter(user=user, room=room).exists():
            return Response(
                {'error': 'Вы не являетесь участником этой чат комнаты.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChatRoomDetailSerializer(room)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Chat'],
    summary="Сообщения чат комнаты",
    description="""
    Получение списка сообщений чат комнаты по её ID.
    
    Возвращает все сообщения комнаты с информацией о пользователях.
    Сообщения отсортированы по дате создания (от старых к новым).
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Параметры:**
    - `room_id` (path parameter) - ID чат комнаты
    - `limit` (query parameter, optional) - Количество сообщений (по умолчанию: 50)
    - `offset` (query parameter, optional) - Смещение для пагинации (по умолчанию: 0)
    
    **Пример запроса:**
    ```
    GET /api/v1/chat/rooms/1/messages/?limit=20&offset=0
    ```
    
    **Пример ответа:**
    ```json
    {
        "messages": [
            {
                "id": 1,
                "room": 1,
                "user": {
                    "id": 1,
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "avatar": "https://example.com/avatar.jpg"
                },
                "message": "Привет! Когда встречаемся?",
                "sender_type": "initiator",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z"
            },
            {
                "id": 2,
                "room": 1,
                "user": {
                    "id": 2,
                    "first_name": "Аня",
                    "last_name": "Иванова",
                    "avatar": "https://example.com/avatar2.jpg"
                },
                "message": "В 19:00 будет удобно?",
                "sender_type": "receiver",
                "created_at": "2025-01-01T12:05:00Z",
                "updated_at": "2025-01-01T12:05:00Z"
            }
        ],
        "count": 15,
        "limit": 20,
        "offset": 0
    }
    ```
    """,
    parameters=[
        OpenApiParameter(
            name='limit',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Количество сообщений для получения (по умолчанию: 50)',
            required=False
        ),
        OpenApiParameter(
            name='offset',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Смещение для пагинации (по умолчанию: 0)',
            required=False
        ),
    ],
    responses={
        200: {
            'description': 'Сообщения успешно получены.',
            'content': {
                'application/json': {
                    'example': {
                        'messages': [],
                        'count': 0,
                        'limit': 50,
                        'offset': 0
                    }
                }
            }
        },
        403: {
            'description': 'Пользователь не является участником этой комнаты.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы не являетесь участником этой чат комнаты.'
                    }
                }
            }
        },
        404: {
            'description': 'Чат комната не найдена.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Не найдено.'
                    }
                }
            }
        },
        401: {
            'description': 'Токен не предоставлен или недействителен.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Учетные данные не были предоставлены.'
                    }
                }
            }
        }
    }
)
class ChatRoomMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        
        user = request.user
        if not ChatRoomGroup.objects.filter(user=user, room=room).exists():
            return Response(
                {'error': 'Вы не являетесь участником этой чат комнаты.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        messages = ChatRoomMessage.objects.filter(room=room).order_by('created_at')
        total_count = messages.count()
        
        messages = messages[offset:offset + limit]
        
        serializer = ChatRoomMessageSerializer(messages, many=True, context={'request': request})
        
        return Response({
            'messages': serializer.data,
            'count': total_count,
            'limit': limit,
            'offset': offset
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Список уведомлений",
    description="""
    Получение списка непрочитанных уведомлений текущего пользователя.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Возвращает только непрочитанные уведомления (is_read=False).
    
    **Пример ответа:**
    ```json
    {
        "notifications": [
            {
                "id": 1,
                "notification_type": "chat_message",
                "title": "Новое сообщение в плане \"Пицца с Аней\"",
                "message": "Иван написал: Привет! Когда встречаемся?...",
                "data": {
                    "room_id": 1,
                    "message_id": 5,
                    "sender_id": 1,
                    "plan_id": 1
                },
                "is_read": false,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z"
            }
        ]
    }
    ```
    """,
    responses={
        200: {
            'description': 'Список уведомлений успешно получен.',
            'content': {
                'application/json': {
                    'example': {
                        'notifications': []
                    }
                }
            }
        },
        401: {
            'description': 'Токен не предоставлен или недействителен.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Учетные данные не были предоставлены.'
                    }
                }
            }
        }
    }
)
class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')
        
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'notifications': serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Получить уведомление по ID",
    description="""
    Получение уведомления по ID и пометка его как прочитанного.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    При получении уведомления оно автоматически помечается как прочитанное (is_read=True).
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "notification_type": "chat_message",
        "title": "Новое сообщение в плане \"Пицца с Аней\"",
        "message": "Иван написал: Привет! Когда встречаемся?...",
        "data": {
            "room_id": 1,
            "message_id": 5,
            "sender_id": 1,
            "plan_id": 1
        },
        "is_read": true,
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:05:00Z"
    }
    ```
    """,
    responses={
        200: OpenApiResponse(
            response=NotificationSerializer,
            description='Уведомление успешно получено и помечено как прочитанное.'
        ),
        403: {
            'description': 'Уведомление принадлежит другому пользователю.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы не можете просматривать это уведомление.'
                    }
                }
            }
        },
        404: {
            'description': 'Уведомление не найдено.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Не найдено.'
                    }
                }
            }
        },
        401: {
            'description': 'Токен не предоставлен или недействителен.',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Учетные данные не были предоставлены.'
                    }
                }
            }
        }
    }
)
class NotificationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id)
        
        if notification.user != request.user:
            return Response(
                {'error': 'Вы не можете просматривать это уведомление.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.is_read = True
        notification.save()
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Chat"],
    summary="Удалить пользователя из чат комнаты",
    description="""
    Удаление пользователя из чат комнаты.

    **Требуется аутентификация:** Да (JWT)

    **Права доступа:**
    - Только создатель плана может удалять пользователей
    - Нельзя удалить самого себя

    **URL параметры:**
    - `room_id` — ID чат комнаты
    - `user_id` — ID пользователя для удаления

    **Пример запроса:**
    ```
    DELETE /api/v1/chat/rooms/1/remove-user/2/
    ```

    **Пример ответа:**
    ```json
    {
        "message": "Пользователь успешно удален из чат комнаты.",
        "room_id": 1,
        "removed_user_id": 2,
        "plan_id": 1
    }
    ```
    """,
    responses={
        200: {"description": "Пользователь успешно удален"},
        400: {"description": "Ошибка запроса"},
        403: {"description": "Нет прав"},
        404: {"description": "Чат комната не найдена"},
        401: {"description": "Не авторизован"},
    },
)
class RemoveUserFromRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, room_id: int, user_id: int):
        """
        ChatRoomGroup dan userni o'chiradi
        va PlanUser status ni REMOVED_INTO_CHAT_GROUP ga o'zgartiradi
        """
        User = get_user_model()

        # Chat roomni topamiz
        room = get_object_or_404(ChatRoom, id=room_id)

        # Faqat plan creator o‘chira oladi
        if room.plan.user != request.user:
            return Response(
                {"error": "Только создатель плана может удалять пользователей из чат комнаты."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # O'zini o‘chirish mumkin emas
        if user_id == request.user.id:
            return Response(
                {"error": "Вы не можете удалить себя из комнаты."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Userni topamiz
        user_to_remove = get_object_or_404(User, id=user_id)

        # ChatRoomGroup mavjudligini tekshiramiz
        chat_room_group = ChatRoomGroup.objects.filter(
            room=room,
            user=user_to_remove
        ).first()

        if not chat_room_group:
            return Response(
                {"error": "Пользователь не найден в этой чат комнате."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # PlanUser statusni yangilaymiz
        plan = room.plan
        plan_user, created = PlanUser.objects.get_or_create(
            plan=plan,
            user=user_to_remove,
            defaults={"status": PlanUser.Status.REMOVED_INTO_CHAT_GROUP},
        )

        if not created:
            plan_user.status = PlanUser.Status.REMOVED_INTO_CHAT_GROUP
            plan_user.save(update_fields=["status", "updated_at"])

        # ChatRoomGroup dan o‘chiramiz
        chat_room_group.delete()

        return Response(
            {
                "message": "Пользователь успешно удален из чат комнаты.",
                "room_id": room_id,
                "removed_user_id": user_id,
                "plan_id": plan.id,
            },
            status=status.HTTP_200_OK,
        )
