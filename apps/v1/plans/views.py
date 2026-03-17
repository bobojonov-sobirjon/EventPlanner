import uuid
import requests
import json
import base64
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.conf import settings

from .serializers import (
    PlanSerializer, PlanCreateSerializer, PlanUpdateSerializer,
    PlanApproveRejectSerializer, PlanUserSerializer,
    FriendSerializer, PlanFriendsBulkTokenSerializer, GenerateTokenPlanSerializer
)
from .models import Plan, PlanUser, GenerateTokenPlan
from apps.v1.chat.models import ChatRoom, ChatRoomGroup


@extend_schema(
    tags=['Plans'],
    summary="Создать план",
    description="""
    Создание нового плана.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Пример запроса:**
    ```json
    {
        "emoji": "🍕",
        "name": "Пицца с Аней",
        "location": "Додо Пицца, Тверская 10",
        "lat": "55.7558",
        "lng": "37.6173",
        "datetime": "2025-12-27T19:00:00"
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "emoji": "🍕",
        "name": "Пицца с Аней",
        "location": "Додо Пицца, Тверская 10",
        "lat": "55.7558",
        "lng": "37.6173",
        "datetime": "2025-12-27T19:00:00Z",
        "user": {
            "id": 1,
            "first_name": "Иван",
            "last_name": "Иванов",
            ...
        },
        "plan_users": [],
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z"
    }
    ```
    """,
    request=PlanCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=PlanSerializer,
            description='План успешно создан.'
        ),
        400: {
            'description': 'Ошибка валидации данных.',
            'content': {
                'application/json': {
                    'example': {
                        'name': ['Это поле обязательно.']
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
class PlanCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan = Plan.objects.create(
            user=request.user,
            **serializer.validated_data
        )
        
        # Creator uchun PlanUser yaratish (status APPROVED)
        plan_user, created = PlanUser.objects.get_or_create(
            plan=plan,
            user=request.user,
            defaults={
                'status': PlanUser.Status.APPROVED
            }
        )
        # Agar allaqachon mavjud bo'lsa va creator bo'lsa, status'ni APPROVED qilish
        if not created and plan.user == request.user:
            plan_user.status = PlanUser.Status.APPROVED
            plan_user.save(update_fields=['status', 'updated_at'])
        
        chat_room = ChatRoom.objects.create(
            plan=plan,
            user=request.user
        )
        
        ChatRoomGroup.objects.create(
            user=request.user,
            room=chat_room
        )
        
        return Response(PlanSerializer(plan).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Plans'],
    summary="Список планов пользователя",
    description="""
    Получение списка всех планов текущего аутентифицированного пользователя с возможностью фильтрации.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Параметры фильтрации:**
    - `filter_type` (query parameter) - Тип фильтра: `new` (новые за 2 дня) или `date` (по дате)
    - `date` (query parameter) - Конкретная дата для фильтрации (формат: YYYY-MM-DD). Возвращает планы на указанную дату
    - `start_date` (query parameter) - Начальная дата (формат: YYYY-MM-DD)
    - `end_date` (query parameter) - Конечная дата (формат: YYYY-MM-DD)
    
    Возвращает планы в двух категориях:
    1. **approved_and_yours_plans** - Планы, созданные пользователем (Plan.user) и планы, где пользователь является участником со статусом "approved" (PlanUser)
    2. **pending_plans** - Планы, где пользователь имеет статус "pending" (PlanUser со статусом pending)
    
    **Пример запроса:**
    ```
    GET /api/v1/plans/list/?filter_type=new
    GET /api/v1/plans/list/?date=2025-12-27
    GET /api/v1/plans/list/?filter_type=date&start_date=2025-12-01&end_date=2025-12-31
    ```
    
    **Пример ответа:**
    ```json
    {
        "approved_and_yours_plans": [
            {
                "id": 1,
                "emoji": "🍕",
                "name": "Пицца с Аней",
                "location": "Додо Пицца, Тверская 10",
                "datetime": "2025-12-27T19:00:00Z",
                "user": {...},
                "plan_users": [...],
                "count_user": 3
            }
        ],
        "pending_plans": [
            {
                "id": 2,
                "emoji": "🎬",
                "name": "Кино с друзьями",
                "location": "Кинотеатр",
                "datetime": "2025-12-28T20:00:00Z",
                "user": {...},
                "plan_users": [...],
                "count_user": 2
            }
        ]
    }
    ```
    """,
    parameters=[
        OpenApiParameter(
            name='filter_type',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Тип фильтра: "new" (новые за 2 дня) или "date" (по дате)',
            required=False,
            enum=['new', 'date']
        ),
        OpenApiParameter(
            name='date',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Конкретная дата для фильтрации (формат: YYYY-MM-DD). Возвращает планы на указанную дату',
            required=False
        ),
        OpenApiParameter(
            name='start_date',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Начальная дата для фильтрации (формат: YYYY-MM-DD)',
            required=False
        ),
        OpenApiParameter(
            name='end_date',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Конечная дата для фильтрации (формат: YYYY-MM-DD)',
            required=False
        ),
    ],
    responses={
        200: {
            'description': 'Список планов успешно получен.',
            'content': {
                'application/json': {
                    'example': {
                        'approved_and_yours_plans': [],
                        'pending_plans': []
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
class PlanListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        filter_type = request.query_params.get('filter_type')
        date = request.query_params.get('date')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        approved_and_yours_plans = Plan.objects.filter(
            Q(user=user) | Q(plan_users__user=user, plan_users__status=PlanUser.Status.APPROVED)
        ).distinct()
        
        pending_plans = Plan.objects.filter(
            plan_users__user=user,
            plan_users__status=PlanUser.Status.PENDING
        ).distinct()
        
        # Filter type ustuvor bo'lishi kerak
        if filter_type == 'new':
            # "new" filter: oxirgi 2 kun ichida yaratilgan planlar (date parametri e'tiborga olinmaydi)
            two_days_ago = datetime.now() - timedelta(days=2)
            approved_and_yours_plans = approved_and_yours_plans.filter(created_at__gte=two_days_ago)
            pending_plans = pending_plans.filter(created_at__gte=two_days_ago)
        elif filter_type == 'date' or (not filter_type and (date or start_date or end_date)):
            # "date" filter yoki filter_type bo'lmasa ham date parametrlar mavjud bo'lsa
            if date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                    approved_and_yours_plans = approved_and_yours_plans.filter(
                        datetime__gte=start_of_day,
                        datetime__lte=end_of_day
                    )
                    pending_plans = pending_plans.filter(
                        datetime__gte=start_of_day,
                        datetime__lte=end_of_day
                    )
                except ValueError:
                    pass
            else:
                # start_date va end_date ishlatish
                if start_date:
                    try:
                        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                        approved_and_yours_plans = approved_and_yours_plans.filter(datetime__gte=start_datetime)
                        pending_plans = pending_plans.filter(datetime__gte=start_datetime)
                    except ValueError:
                        pass
                if end_date:
                    try:
                        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                        end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                        approved_and_yours_plans = approved_and_yours_plans.filter(datetime__lte=end_datetime)
                        pending_plans = pending_plans.filter(datetime__lte=end_datetime)
                    except ValueError:
                        pass
        
        approved_serializer = PlanSerializer(approved_and_yours_plans, many=True)
        pending_serializer = PlanSerializer(pending_plans, many=True)
        
        return Response({
            'approved_and_yours_plans': approved_serializer.data,
            'pending_plans': pending_serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plans'],
    summary="Получить план по ID",
    description="""
    Получение детальной информации о плане по его ID.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "emoji": "🍕",
        "name": "Пицца с Аней",
        "location": "Додо Пицца, Тверская 10",
        "lat": "55.7558",
        "lng": "37.6173",
        "datetime": "2025-12-27T19:00:00Z",
        "user": {...},
        "tokens": [...],
        "plan_users": [...]
    }
    ```
    """,
    responses={
        200: OpenApiResponse(
            response=PlanSerializer,
            description='План успешно получен.'
        ),
        404: {
            'description': 'План не найден.',
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
class PlanDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, plan_id):
        plan = get_object_or_404(Plan, id=plan_id)
        serializer = PlanSerializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Generate Token Plans'],
    summary="Сгенерировать токен для плана",
    description="""
    Генерация invite-ссылки для плана.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Этот endpoint используется для создания invite-ссылки для плана.
    Пользователь автоматически добавляется в PlanUser со статусом PENDING.
    
    **Пример запроса:**
    ```
    POST /api/v1/plans/1/generate-token/
    ```
    
    **Пример ответа:**
    ```json
    {
        "plan_id": 1,
        "link": "https://t.me/your_bot?start=1",
        "msg": "Иван приглашает вас на план «Пицца с Аней» на 27.12.2025 19:00. Присоединяйтесь: https://t.me/your_bot?start=1"
    }
    ```
    """,
    responses={
        201: {
            'description': 'Ссылка успешно создана.',
            'content': {
                'application/json': {
                    'example': {
                        'plan_id': 1,
                        'link': 'https://t.me/your_bot?start=1',
                        'msg': 'Иван приглашает вас на план «Пицца с Аней» на 27.12.2025 19:00. Присоединяйтесь: https://t.me/your_bot?start=1'
                    }
                }
            }
        },
        403: {
            'description': 'Недостаточно прав для генерации токена.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы можете генерировать токены только для своих планов.'
                    }
                }
            }
        },
        404: {
            'description': 'План не найден.',
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
class PlanGenerateTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, plan_id):
        from .models import GenerateTokenPlan
        from datetime import timedelta
        from django.utils import timezone
        import uuid
        
        plan = get_object_or_404(Plan, id=plan_id)
        
        if plan.user != request.user:
            return Response(
                {'error': 'Вы можете генерировать токены только для своих планов.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Request user ni PlanUser ga qo'shish
        # Agar creator bo'lsa APPROVED, aks holda PENDING
        plan_user, created = PlanUser.objects.get_or_create(
            plan=plan,
            user=request.user,
            defaults={
                'status': PlanUser.Status.APPROVED if plan.user == request.user else PlanUser.Status.PENDING
            }
        )
        # Agar allaqachon mavjud bo'lsa va creator bo'lsa, status'ni APPROVED qilish
        if not created and plan.user == request.user:
            plan_user.status = PlanUser.Status.APPROVED
            plan_user.save(update_fields=['status', 'updated_at'])
        
        # Xavfsiz token yaratish
        # Max uses va expiration sozlamalari (default: 10 ta foydalanish, 30 kun muddat)
        max_uses = request.data.get('max_uses', 10)
        expires_days = request.data.get('expires_days', 30)
        
        # Token yaratish
        token_id = uuid.uuid4()
        token_str = str(token_id).replace('-', '')[:32]  # 32 ta belgi
        
        expires_at = timezone.now() + timedelta(days=expires_days) if expires_days > 0 else None
        
        token_obj = GenerateTokenPlan.objects.create(
            id=token_id,
            token=token_str,
            plan=plan,
            created_by=request.user,
            expires_at=expires_at,
            max_uses=max_uses,
            is_active=True
        )
        
        bot_name = getattr(settings, 'BOT_NAME', 'your_bot')
        # Link yaratish: token ishlatamiz, plan_id emas
        link = f"https://t.me/{bot_name}/direclink?startapp={token_str}"
        
        # Получаем данные отправителя
        sender_name = f"{request.user.first_name or ''} {request.user.last_name or ''}".strip()
        if not sender_name:
            sender_name = request.user.username or f"User {request.user.id}"
        
        # Форматируем дату плана (Moscow timezone da)
        dt = plan.datetime
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_default_timezone())
        else:
            dt = dt.astimezone(timezone.get_default_timezone())
        plan_datetime = dt.strftime('%d.%m.%Y %H:%M')
        msg = f"{sender_name} приглашает вас на встречу «{plan.name}» на {plan_datetime}. Присоединяйтесь: {link}"
        
        return Response({
            'plan_id': plan_id,
            'token': token_str,
            'link': link,
            'msg': msg,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'max_uses': max_uses
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Plans'],
    summary="Обновить план",
    description="""
    Обновление информации о плане.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Обновить план может только его создатель.
    
    **Пример запроса:**
    ```json
    {
        "name": "Обновленное название",
        "location": "Новое местоположение",
        "datetime": "2025-12-28T20:00:00"
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "emoji": "🍕",
        "name": "Обновленное название",
        "location": "Новое местоположение",
        "datetime": "2025-12-28T20:00:00Z",
        ...
    }
    ```
    """,
    request=PlanUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=PlanSerializer,
            description='План успешно обновлен.'
        ),
        400: {
            'description': 'Ошибка валидации данных.',
            'content': {
                'application/json': {
                    'example': {
                        'datetime': ['Неверный формат даты.']
                    }
                }
            }
        },
        403: {
            'description': 'Недостаточно прав для обновления плана.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы можете обновлять только свои планы.'
                    }
                }
            }
        },
        404: {
            'description': 'План не найден.',
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
class PlanUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, plan_id):
        plan = get_object_or_404(Plan, id=plan_id)
        
        if plan.user != request.user:
            return Response(
                {'error': 'Вы можете обновлять только свои планы.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlanUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        for attr, value in serializer.validated_data.items():
            setattr(plan, attr, value)
        plan.save()
        
        return Response(PlanSerializer(plan).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plan Invitations'],
    summary="Принять приглашение на план",
    description="""
    Принятие приглашения на план.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Когда пользователь нажимает "Принять",
    создается или обновляется запись PlanUser со статусом "approved".
    
    **Пример запроса:**
    ```json
    {
        "plan_id": 1
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "plan": 1,
        "user": {...},
        "status": "approved",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z"
    }
    ```
    """,
    request=PlanApproveRejectSerializer,
    responses={
        200: OpenApiResponse(
            response=PlanUserSerializer,
            description='Приглашение успешно принято.'
        ),
        400: {
            'description': 'Ошибка валидации или план не найден.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'План не найден.'
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
class PlanApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = PlanApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan_id = serializer.validated_data['plan_id']
        
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'План не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # PlanUser ni topamiz yoki yaratamiz
        plan_user, created = PlanUser.objects.update_or_create(
            plan=plan,
            user=request.user,
            defaults={
                'status': PlanUser.Status.APPROVED
            }
        )
        
        try:
            chat_room = ChatRoom.objects.get(plan=plan)
            chat_group, created_group = ChatRoomGroup.objects.get_or_create(
                user=request.user,
                room=chat_room
            )
            print(f"[DEBUG] PlanApprove - User ID: {request.user.id} added to ChatRoomGroup for room {chat_room.id}, created: {created_group}")
        except ChatRoom.DoesNotExist:
            print(f"[DEBUG] PlanApprove - ChatRoom not found for plan {plan.id}")
            pass
        
        return Response(PlanUserSerializer(plan_user).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plan Invitations'],
    summary="Отклонить приглашение на план",
    description="""
    Отклонение приглашения на план.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Когда пользователь нажимает "Отклонить",
    создается или обновляется запись PlanUser со статусом "rejected".
    
    **Пример запроса:**
    ```json
    {
        "plan_id": 1
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "plan": 1,
        "user": {...},
        "status": "rejected",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z"
    }
    ```
    """,
    request=PlanApproveRejectSerializer,
    responses={
        200: OpenApiResponse(
            response=PlanUserSerializer,
            description='Приглашение успешно отклонено.'
        ),
        400: {
            'description': 'Ошибка валидации или план не найден.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'План не найден.'
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
class PlanRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = PlanApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan_id = serializer.validated_data['plan_id']
        
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'План не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # PlanUser ni topamiz yoki yaratamiz
        plan_user, created = PlanUser.objects.update_or_create(
            plan=plan,
            user=request.user,
            defaults={
                'status': PlanUser.Status.REJECTED
            }
        )
        
        try:
            chat_room = ChatRoom.objects.get(plan=plan)
            chat_group, created_group = ChatRoomGroup.objects.get_or_create(
                user=request.user,
                room=chat_room
            )
            print(f"[DEBUG] PlanReject - User ID: {request.user.id} added to ChatRoomGroup for room {chat_room.id}, created: {created_group}")
        except ChatRoom.DoesNotExist:
            print(f"[DEBUG] PlanReject - ChatRoom not found for plan {plan.id}")
            pass
        
        return Response(PlanUserSerializer(plan_user).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plans'],
    summary="Удалить план",
    description="""
    Удаление плана.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Удалить план может только его создатель.
    При удалении плана также удаляются все связанные токены и записи PlanUser.
    
    **Пример ответа:**
    ```json
    {
        "message": "План успешно удален."
    }
    ```
    """,
    responses={
        200: {
            'description': 'План успешно удален.',
            'content': {
                'application/json': {
                    'example': {
                        'message': 'План успешно удален.'
                    }
                }
            }
        },
        403: {
            'description': 'Недостаточно прав для удаления плана.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы можете удалять только свои планы.'
                    }
                }
            }
        },
        404: {
            'description': 'План не найден.',
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
class PlanDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, plan_id):
        plan = get_object_or_404(Plan, id=plan_id)
        
        if plan.user != request.user:
            return Response(
                {'error': 'Вы можете удалять только свои планы.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        plan.delete()
        return Response(
            {'message': 'План успешно удален.'},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Plans'],
    summary="Список друзей пользователя",
    description="""
    Получение списка всех друзей текущего аутентифицированного пользователя.
    
    Друзьями считаются пользователи, которые участвуют в одних и тех же планах
    (либо как создатель, либо как участник со статусом "approved").
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Пример ответа:**
    ```json
    {
        "friends": [
            {
                "user": {
                    "id": 2,
                    "first_name": "Аня",
                    "last_name": "Иванова",
                    "phone": "+1234567890",
                    "avatar": "https://example.com/avatar.jpg"
                },
                "plan_ids": [1, 5, 8],
                "plans_count": 3
            },
            {
                "user": {
                    "id": 3,
                    "first_name": "Макс",
                    "last_name": "Петров",
                    "phone": "+1234567891",
                    "avatar": "https://example.com/avatar2.jpg"
                },
                "plan_ids": [2, 7],
                "plans_count": 2
            }
        ]
    }
    ```
    """,
    responses={
        200: {
            'description': 'Список друзей успешно получен.',
            'content': {
                'application/json': {
                    'example': {
                        'friends': []
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
class FriendsListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        user_plans = Plan.objects.filter(
            Q(user=user) | Q(plan_users__user=user, plan_users__status=PlanUser.Status.APPROVED)
        ).distinct()
        
        friends_dict = {}
        
        for plan in user_plans:
            if plan.user != user:
                friend_id = plan.user.id
                if friend_id not in friends_dict:
                    friends_dict[friend_id] = {
                        'user': plan.user,
                        'plan_ids': []
                    }
                if plan.id not in friends_dict[friend_id]['plan_ids']:
                    friends_dict[friend_id]['plan_ids'].append(plan.id)
            
            approved_users = plan.plan_users.filter(status=PlanUser.Status.APPROVED).exclude(user=user)
            for plan_user in approved_users:
                friend_id = plan_user.user.id
                if friend_id not in friends_dict:
                    friends_dict[friend_id] = {
                        'user': plan_user.user,
                        'plan_ids': []
                    }
                if plan.id not in friends_dict[friend_id]['plan_ids']:
                    friends_dict[friend_id]['plan_ids'].append(plan.id)
        
        friends_list = list(friends_dict.values())
        serializer = FriendSerializer(friends_list, many=True)
        
        return Response({
            'friends': serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plans'],
    summary="Список друзей для плана",
    description="""
    Получение списка всех друзей текущего пользователя, которые участвовали в планах.
    
    Друзья определяются через PlanUser модель - пользователи, которые участвовали
    в планах вместе с текущим пользователем (либо как создатель, либо как участник).
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Пример ответа:**
    ```json
    {
        "friends": [
            {
                "user": {
                    "id": 2,
                    "first_name": "Аня",
                    "last_name": "Иванова",
                    "tg_id": 123456789,
                    "avatar": "https://example.com/avatar.jpg"
                },
                "plan_ids": [1, 5, 8],
                "plans_count": 3
            }
        ]
    }
    ```
    """,
    responses={
        200: {
            'description': 'Список друзей успешно получен.',
            'content': {
                'application/json': {
                    'example': {
                        'friends': []
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
class PlanFriendsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        user_plans = Plan.objects.filter(
            Q(user=user) | Q(plan_users__user=user)
        ).distinct()
        
        friends_dict = {}
        
        for plan in user_plans:
            plan_users = PlanUser.objects.filter(plan=plan).exclude(user=user)
            for plan_user in plan_users:
                friend_id = plan_user.user.id
                if friend_id not in friends_dict:
                    friends_dict[friend_id] = {
                        'user': plan_user.user,
                        'plan_ids': []
                    }
                if plan.id not in friends_dict[friend_id]['plan_ids']:
                    friends_dict[friend_id]['plan_ids'].append(plan.id)
        
        friends_list = list(friends_dict.values())
        serializer = FriendSerializer(friends_list, many=True)
        
        return Response({
            'friends': serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Generate Token Plans'],
    summary="Отправить приглашения друзьям",
    description="""
    Отправка приглашений на план нескольким друзьям одновременно через Telegram.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Этот endpoint отправляет приглашения выбранным пользователям через Telegram.
    Ссылка создается с plan_id: `https://t.me/{bot_name}?start={plan_id}`
    Все пользователи автоматически добавляются в PlanUser со статусом PENDING.
    
    **Пример запроса:**
    ```json
    {
        "user_ids": [2, 3, 4]
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "message": "Приглашения отправлены 3 пользователям.",
        "sent_count": 3,
        "total_users": 3,
        "link": "https://t.me/event_planner_mini_bot?start=1",
        "errors": null
    }
    ```
    """,
    request=PlanFriendsBulkTokenSerializer,
    responses={
        200: {
            'description': 'Приглашения успешно отправлены.',
            'content': {
                'application/json': {
                    'example': {
                        'message': 'Приглашения отправлены 3 пользователям.',
                        'sent_count': 3,
                        'total_users': 3,
                        'link': 'https://t.me/event_planner_mini_bot?start=1',
                        'errors': None
                    }
                }
            }
        },
        400: {
            'description': 'Ошибка валидации или пользователи не найдены.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Некоторые пользователи не найдены.'
                    }
                }
            }
        },
        403: {
            'description': 'Недостаточно прав для генерации токенов.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Вы можете генерировать токены только для своих планов.'
                    }
                }
            }
        },
        404: {
            'description': 'План не найден.',
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
class PlanFriendsBulkTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, plan_id):
        plan = get_object_or_404(Plan, id=plan_id)
        
        if plan.user != request.user:
            return Response(
                {'error': 'Вы можете генерировать токены только для своих планов.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlanFriendsBulkTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_ids = serializer.validated_data['user_ids']
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users = User.objects.filter(id__in=user_ids)
        if users.count() != len(user_ids):
            return Response(
                {'error': 'Некоторые пользователи не найдены.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        bot_name = getattr(settings, 'BOT_NAME', 'your_bot')
        
        # Получаем данные отправителя
        sender_name = f"{request.user.first_name or ''} {request.user.last_name or ''}".strip()
        if not sender_name:
            sender_name = request.user.username or f"User {request.user.id}"
        
        # Xavfsiz token yaratish (bulk invite uchun - ko'p foydalanish mumkin)
        from .models import GenerateTokenPlan
        from datetime import timedelta
        from django.utils import timezone
        import uuid
        
        # Форматируем дату плана (Moscow timezone da)
        dt = plan.datetime
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_default_timezone())
        else:
            dt = dt.astimezone(timezone.get_default_timezone())
        plan_datetime = dt.strftime('%d.%m.%Y %H:%M')
        
        # Bulk invite uchun max_uses = userlar soni + bir nechta qo'shimcha
        max_uses = len(user_ids) + 5  # 5 ta qo'shimcha imkoniyat
        expires_days = 30
        
        token_id = uuid.uuid4()
        token_str = str(token_id).replace('-', '')[:32]
        expires_at = timezone.now() + timedelta(days=expires_days)
        
        token_obj = GenerateTokenPlan.objects.create(
            id=token_id,
            token=token_str,
            plan=plan,
            created_by=request.user,
            expires_at=expires_at,
            max_uses=max_uses,
            is_active=True
        )
        
        # Barcha userlarni PlanUser ga qo'shish
        # Creator uchun APPROVED, boshqalar uchun PENDING
        for user in users:
            plan_user, created = PlanUser.objects.get_or_create(
                plan=plan,
                user=user,
                defaults={
                    'status': PlanUser.Status.APPROVED if plan.user == user else PlanUser.Status.PENDING
                }
            )
            # Agar allaqachon mavjud bo'lsa va creator bo'lsa, status'ni APPROVED qilish
            if not created and plan.user == user:
                plan_user.status = PlanUser.Status.APPROVED
                plan_user.save(update_fields=['status', 'updated_at'])
        
        # Link yaratish: token ishlatamiz
        invite_link = f"https://t.me/{bot_name}/direclink?startapp={token_str}"
        
        # Формируем сообщение
        message_text = f"{sender_name} приглашает вас на встречу «{plan.name}» на {plan_datetime}. Присоединяйтесь: {invite_link}"
        
        sent_count = 0
        errors = []
        
        # [DEBUG] Bot token va userlar tg_id tekshiruvi
        print(f"[PlanFriendsBulkToken] TELEGRAM_BOT_TOKEN bor: {bool(bot_token)}")
        print(f"[PlanFriendsBulkToken] BOT_NAME: {bot_name}")
        print(f"[PlanFriendsBulkToken] Invite qilinadigan userlar soni: {len(users)}")
        for u in users:
            tg_id = getattr(u, 'tg_id', None)
            telegram_id = getattr(u, 'telegram_id', None)
            print(f"[PlanFriendsBulkToken] User id={u.id}, first_name={getattr(u, 'first_name', '')}, tg_id={tg_id}, telegram_id={telegram_id}")
        
        if not bot_token:
            return Response(
                {'error': 'TELEGRAM_BOT_TOKEN не настроен. Добавьте токен бота в .env или настройки.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Bot API orqali har bir do'stga (tg_id bor bo'lsa) xabar yuborish
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        for user in users:
            # tg_id yoki telegram_id (legacy) — Telegramda chat_id
            chat_id = getattr(user, 'tg_id', None) or getattr(user, 'telegram_id', None)
            if not chat_id:
                print(f"[PlanFriendsBulkToken] User {user.id} — tg_id yo'q, xabar yuborilmaydi")
                errors.append(f"User {user.id} ({getattr(user, 'first_name', '')}): нет Telegram ID (пользователь не входил через Telegram)")
                continue
            try:
                payload = {
                    'chat_id': chat_id,
                    'text': message_text,
                }
                response = requests.post(telegram_api_url, json=payload, timeout=10)
                if response.status_code == 200:
                    sent_count += 1
                    print(f"[PlanFriendsBulkToken] User {user.id} (tg_id={chat_id}) — xabar yuborildi OK")
                else:
                    try:
                        err_body = response.json()
                        err_desc = err_body.get('description', response.text)
                    except Exception:
                        err_desc = response.text
                    print(f"[PlanFriendsBulkToken] User {user.id} (tg_id={chat_id}) — Telegram API xato: {response.status_code} — {err_desc}")
                    errors.append(f"User {user.id} (tg_id={chat_id}): {response.status_code} — {err_desc}")
            except Exception as e:
                print(f"[PlanFriendsBulkToken] User {user.id} — Exception: {e}")
                errors.append(f"User {user.id}: {str(e)}")
        print(f"[PlanFriendsBulkToken] Yakuniy: sent_count={sent_count}, errors={len(errors)}")
        
        return Response({
            'message': f'Приглашения отправлены {sent_count} пользователям.',
            'sent_count': sent_count,
            'total_users': len(users),
            'link': invite_link,
            'errors': errors if errors else None
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plans'],
    summary="Получить информацию о токене приглашения",
    description="""
    Получение информации о токене приглашения по токену.
    
    **Требуется аутентификация:** Нет (публичный endpoint)
    
    Этот endpoint используется для получения информации о токене приглашения.
    Можно использовать для проверки валидности токена перед использованием.
    
    **Пример запроса:**
    ```
    GET /api/v1/plans/token/a1b2c3d4e5f6.../
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "token": "a1b2c3d4e5f6...",
        "plan": {
            "id": 1,
            "name": "Пицца с Аней",
            ...
        },
        "created_by": {
            "id": 1,
            "username": "user1",
            ...
        },
        "expires_at": "2025-02-23T16:35:00Z",
        "max_uses": 10,
        "current_uses": 3,
        "is_active": true,
        "is_valid": true,
        "created_at": "2025-01-24T16:35:00Z",
        "updated_at": "2025-01-24T16:35:00Z"
    }
    ```
    """,
    parameters=[
        OpenApiParameter(
            name='token',
            type=str,
            location=OpenApiParameter.PATH,
            description='Токен приглашения',
            required=True
        )
    ],
    responses={
        200: OpenApiResponse(
            response=GenerateTokenPlanSerializer,
            description='Информация о токене успешно получена.'
        ),
        404: {
            'description': 'Токен не найден.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Токен не найден.'
                    }
                }
            }
        }
    }
)
class PlanTokenDetailAPIView(APIView):
    permission_classes = []  # Публичный endpoint
    
    def get(self, request, token):
        """
        Token bo'yicha GenerateTokenPlan ma'lumotlarini qaytaradi
        """
        try:
            token_obj = GenerateTokenPlan.objects.get(token=token)
            serializer = GenerateTokenPlanSerializer(token_obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except GenerateTokenPlan.DoesNotExist:
            return Response(
                {'error': 'Токен не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )

