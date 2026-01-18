import uuid
import requests
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.conf import settings

from .serializers import (
    PlanSerializer, PlanCreateSerializer, PlanUpdateSerializer,
    PlanApproveRejectSerializer, PlanUserSerializer, GenerateTokenPlanSerializer,
    FriendSerializer, PlanFriendsBulkTokenSerializer
)
from .models import Plan, GenerateTokenPlan, PlanUser
from apps.v1.chat.models import ChatRoom, ChatRoomGroup


@extend_schema(
    tags=['Plans'],
    summary="Создать план",
    description="""
    Создание нового плана.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    При создании плана токен автоматически не генерируется.
    Для генерации токена используйте отдельный endpoint: POST /api/v1/plans/<plan_id>/generate-token/
    
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
        "tokens": [],
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
                "tokens": [...],
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
                "tokens": [...],
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
        elif filter_type == 'new':
            two_days_ago = datetime.now() - timedelta(days=2)
            approved_and_yours_plans = approved_and_yours_plans.filter(created_at__gte=two_days_ago)
            pending_plans = pending_plans.filter(created_at__gte=two_days_ago)
        elif filter_type == 'date':
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
        
        if start_date and not filter_type and not date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                approved_and_yours_plans = approved_and_yours_plans.filter(datetime__gte=start_datetime)
                pending_plans = pending_plans.filter(datetime__gte=start_datetime)
            except ValueError:
                pass
        
        if end_date and not filter_type and not date:
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


    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {'error': 'Параметр token обязателен.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            token_obj = GenerateTokenPlan.objects.get(token=token)
            
            if token_obj.is_activated:
                existing_plan_user = PlanUser.objects.filter(
                    plan=token_obj.plan,
                    token=token_obj
                ).first()
                
                if existing_plan_user and existing_plan_user.user != request.user:
                    return Response(
                        {'error': 'Этот токен приглашения уже использован другим пользователем.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            plan = token_obj.plan
            
            PlanUser.objects.get_or_create(
                plan=plan,
                token=token_obj,
                user=request.user,
                defaults={'status': PlanUser.Status.PENDING}
            )
            
            if not token_obj.is_activated:
                token_obj.is_activated = True
                token_obj.save()
            
            serializer = PlanSerializer(plan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except GenerateTokenPlan.DoesNotExist:
            return Response(
                {'error': 'План с указанным токеном не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )
@extend_schema(
    tags=['Plan Tokens'],
    summary="Сгенерировать токен для плана",
    description="""
    Генерация нового токена для приглашения друзей на план.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Этот endpoint используется для создания invite-ссылки для каждого друга отдельно.
    Каждый вызов создает новый уникальный токен для одного плана.
    Один план может иметь множество токенов (для разных друзей).
    
    **Пример запроса:**
    ```
    POST /api/v1/plans/1/generate-token/
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "token": "550e8400-e29b-41d4-a716-446655440000",
        "link": "https://t.me/your_bot?start=550e8400-e29b-41d4-a716-446655440000",
        "msg": "Иван приглашает вас на план «Пицца с Аней» на 27.12.2025 19:00. Присоединяйтесь: https://t.me/your_bot?start=550e8400-e29b-41d4-a716-446655440000"
    }
    ```
    """,
    responses={
        201: {
            'description': 'Токен успешно сгенерирован.',
            'content': {
                'application/json': {
                    'example': {
                        'id': 1,
                        'token': '550e8400-e29b-41d4-a716-446655440000',
                        'link': 'https://t.me/your_bot?start=550e8400-e29b-41d4-a716-446655440000',
                        'msg': 'Иван приглашает вас на план «Пицца с Аней» на 27.12.2025 19:00. Присоединяйтесь: https://t.me/your_bot?start=550e8400-e29b-41d4-a716-446655440000'
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
        plan = get_object_or_404(Plan, id=plan_id)
        
        if plan.user != request.user:
            return Response(
                {'error': 'Вы можете генерировать токены только для своих планов.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        token = GenerateTokenPlan.objects.create(
            plan=plan,
            token=str(uuid.uuid4())
        )
        
        return Response(
            GenerateTokenPlanSerializer(token).data,
            status=status.HTTP_201_CREATED
        )


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
    Принятие приглашения на план по токену.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Когда пользователь переходит по invite-ссылке и нажимает "Принять",
    создается или обновляется запись PlanUser со статусом "approved".
    
    **Пример запроса:**
    ```json
    {
        "plan_id": 1,
        "token_id": 1
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "plan": 1,
        "token": {...},
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
            'description': 'Ошибка валидации или план/токен не найден.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'План или токен не найден.'
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
        token_id = serializer.validated_data['token_id']
        
        try:
            plan = Plan.objects.get(id=plan_id)
            try:
                if token_id.isdigit():
                    token = GenerateTokenPlan.objects.get(id=int(token_id), plan=plan)
                else:
                    token = GenerateTokenPlan.objects.get(token=token_id, plan=plan)
            except (GenerateTokenPlan.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Токен не найден.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Plan.DoesNotExist:
            return Response(
                {'error': 'План не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan_user, created = PlanUser.objects.update_or_create(
            plan=plan,
            token=token,
            user=request.user,
            defaults={'status': PlanUser.Status.APPROVED}
        )
        
        try:
            chat_room = ChatRoom.objects.get(plan=plan)
            ChatRoomGroup.objects.get_or_create(
                user=request.user,
                room=chat_room
            )
        except ChatRoom.DoesNotExist:
            pass
        
        return Response(PlanUserSerializer(plan_user).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Plan Invitations'],
    summary="Отклонить приглашение на план",
    description="""
    Отклонение приглашения на план по токену.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Когда пользователь переходит по invite-ссылке и нажимает "Отклонить",
    создается или обновляется запись PlanUser со статусом "rejected".
    
    **Пример запроса:**
    ```json
    {
        "plan_id": 1,
        "token_id": 1
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "plan": 1,
        "token": {...},
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
            'description': 'Ошибка валидации или план/токен не найден.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'План или токен не найден.'
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
        token_id = serializer.validated_data['token_id']
        
        try:
            plan = Plan.objects.get(id=plan_id)
            try:
                if token_id.isdigit():
                    token = GenerateTokenPlan.objects.get(id=int(token_id), plan=plan)
                else:
                    token = GenerateTokenPlan.objects.get(token=token_id, plan=plan)
            except (GenerateTokenPlan.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Токен не найден.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Plan.DoesNotExist:
            return Response(
                {'error': 'План не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan_user, created = PlanUser.objects.update_or_create(
            plan=plan,
            token=token,
            user=request.user,
            defaults={'status': PlanUser.Status.REJECTED}
        )
        
        try:
            chat_room = ChatRoom.objects.get(plan=plan)
            ChatRoomGroup.objects.get_or_create(
                user=request.user,
                room=chat_room
            )
        except ChatRoom.DoesNotExist:
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
    tags=['Plan Tokens'],
    summary="Сгенерировать токены для друзей",
    description="""
    Генерация токенов для нескольких друзей одновременно.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    Этот endpoint позволяет создать токены для нескольких друзей сразу.
    Для каждого пользователя из списка создается отдельный уникальный токен.
    
    **Пример запроса:**
    ```json
    {
        "user_ids": [2, 3, 4]
    }
    ```
    
    **Пример ответа:**
    ```json
    {
        "tokens": [
            {
                "id": 4,
                "token": "cf74dc85-9b08-4e20-8027-074f50c84b0c",
                "link": "https://t.me/event_planner_mini_bot?start=cf74dc85-9b08-4e20-8027-074f50c84b0c",
                "msg": "Sobirjon Bobojonov приглашает вас на план «Пицца с Аней» на 27.12.2025 16:00. Присоединяйтесь: https://t.me/event_planner_mini_bot?start=cf74dc85-9b08-4e20-8027-074f50c84b0c"
            },
            {
                "id": 5,
                "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "link": "https://t.me/event_planner_mini_bot?start=a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "msg": "Sobirjon Bobojonov приглашает вас на план «Пицца с Аней» на 27.12.2025 16:00. Присоединяйтесь: https://t.me/event_planner_mini_bot?start=a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        ]
    }
    ```
    """,
    request=PlanFriendsBulkTokenSerializer,
    responses={
        201: {
            'description': 'Токены успешно сгенерированы.',
            'content': {
                'application/json': {
                    'example': {
                        'tokens': []
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
        
        tokens = []
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        bot_name = getattr(settings, 'BOT_NAME', 'your_bot')
        
        for user in users:
            token = GenerateTokenPlan.objects.create(
                plan=plan,
                token=str(uuid.uuid4())
            )
            tokens.append(token)
            
            if user.tg_id and bot_token:
                try:
                    token_link = f"https://t.me/{bot_name}?start={token.token}"
                    message = GenerateTokenPlanSerializer(token).data.get('msg', '')
                    
                    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        'chat_id': user.tg_id,
                        'text': message,
                        'parse_mode': 'HTML'
                    }
                    
                    response = requests.post(telegram_api_url, json=payload, timeout=5)
                    if response.status_code != 200:
                        pass
                except Exception as e:
                    pass
        
        token_serializer = GenerateTokenPlanSerializer(tokens, many=True)
        
        return Response({
            'tokens': token_serializer.data
        }, status=status.HTTP_201_CREATED)
