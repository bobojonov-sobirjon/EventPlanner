import json
import urllib.parse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.utils import timezone

from .models import CustomUser
from .serializers import (
    CustomUserSerializer, 
    TelegramAuthSerializer
)
from .utils import check_auth, TOKEN
from .parsers import PlainTextJSONParser


@extend_schema(
    tags=['Account'],
    summary="Аутентификация через Telegram",
    description="""
    Аутентификация пользователя через Telegram Mini App и возврат JWT токенов.
    
    **Как использовать:**
    1. Получите initData из Telegram Web App: `window.Telegram.WebApp.initData`
    2. Отправьте POST запрос с initData
    3. Получите access_token и refresh_token для дальнейших запросов
    
    **Пример запроса:**
    ```json
    {
        "initData": "user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22John%22%7D&hash=...",
        "invite_token": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```
    
    **Параметры:**
    - `initData` (обязательно) - Строка initData из Telegram Web App
    - `invite_token` (опционально) - Токен приглашения на план. Если передан, пользователь автоматически добавляется в план со статусом "pending".
    
    **Пример ответа:**
    ```json
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
    ```
    """,
    request=TelegramAuthSerializer,
    responses={
        200: {
            'description': 'Успешная аутентификация. Возвращает JWT токены.',
            'content': {
                'application/json': {
                    'example': {
                        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    }
                }
            }
        },
        400: {
            'description': 'Ошибка валидации. initData обязателен или неверный формат.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'initData — обязательное поле.'
                    }
                }
            }
        },
        403: {
            'description': 'Ошибка аутентификации Telegram. Данные не прошли проверку.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Неправильная аутентификация Telegram'
                    }
                }
            }
        },
        500: {
            'description': 'Внутренняя ошибка сервера.',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Ошибка сервера: ...'
                    }
                }
            }
        }
    }
)
class TelegramAuthAPIView(APIView):
    """
    API для аутентификации через Telegram Mini App.
    
    Проверяет initData из Telegram Web App, создает или обновляет пользователя
    и возвращает JWT токены для дальнейшей работы с API.
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, PlainTextJSONParser]

    def post(self, request):
        init_data_str = request.data.get("initData", "")
        invite_token = request.data.get("invite_token", "").strip()
        
        if not init_data_str:
            return Response(
                {'error': 'initData — обязательное поле.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            parsed = urllib.parse.parse_qs(init_data_str)
            processed_data = {
                k: v[0] if isinstance(v, list) and len(v) == 1 else v
                for k, v in parsed.items()
            }
            
            user_json = processed_data.get("user")
            if not user_json:
                return Response(
                    {'error': 'Нет информации о пользователе'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_data = json.loads(user_json)
            
            if not check_auth(processed_data, TOKEN):
                return Response(
                    {'error': 'Неправильная аутентификация Telegram'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            telegram_id = user_data.get("id")
            if not telegram_id:
                return Response(
                    {'error': 'Требуется идентификатор Telegram'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            username = user_data.get("username", f"tg_{telegram_id}")
            first_name = user_data.get("first_name", "")
            last_name = user_data.get("last_name", "")
            telegram_username = user_data.get("username", "")
            photo_url = user_data.get("photo_url", "")
            phone = user_data.get("phone_number", None)

            defaults = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'telegram_username': telegram_username,
                'phone': phone,
                'avatar': photo_url if photo_url else None,
                'tg_id': telegram_id,
            }

            user, created = CustomUser.objects.update_or_create(
                tg_id=telegram_id,
                defaults=defaults
            )

            if invite_token:
                from apps.v1.plans.models import GenerateTokenPlan, PlanUser
                
                try:
                    token_obj = GenerateTokenPlan.objects.get(token=invite_token)
                    
                    # Token hali ham amal qiladimi tekshirish
                    if not token_obj.can_be_used():
                        if not token_obj.is_active:
                            error_msg = 'Этот токен приглашения деактивирован.'
                        elif token_obj.expires_at and timezone.now() > token_obj.expires_at:
                            error_msg = 'Срок действия этого токена приглашения истек.'
                        elif token_obj.current_uses >= token_obj.max_uses:
                            error_msg = 'Этот токен приглашения достиг максимального количества использований.'
                        else:
                            error_msg = 'Этот токен приглашения недействителен.'
                        
                        return Response(
                            {'error': error_msg},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    plan = token_obj.plan
                    
                    # Foydalanuvchini planga qo'shish
                    # Creator bo'lsa APPROVED, aks holda PENDING
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
                    
                    # Agar yangi qo'shilgan bo'lsa, tokenni ishlatish
                    if created:
                        token_obj.use_token()
                    
                except GenerateTokenPlan.DoesNotExist:
                    # Token topilmasa, xato qaytarmaymiz (faqat log qilamiz)
                    pass

            refresh = RefreshToken.for_user(user)
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            return Response(
                {'error': 'Неверный формат JSON'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Account'],
    summary="Профиль пользователя",
    description="""
    Получение профиля аутентифицированного пользователя.
    
    **Требуется аутентификация:** Да (JWT токен в заголовке Authorization)
    
    **Пример запроса:**
    ```
    GET /api/v1/accounts/profile/
    Authorization: Bearer <access_token>
    ```
    
    **Пример ответа:**
    ```json
    {
        "id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "email": "user@example.com",
        "avatar": "https://example.com/avatar.jpg",
    }
    ```
    """,
    responses={
        200: OpenApiResponse(
            response=CustomUserSerializer,
            description='Профиль пользователя успешно получен.'
        ),
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
class UserProfileAPIView(APIView):
    """
    API для получения профиля пользователя.
    
    Возвращает полную информацию о текущем аутентифицированном пользователе.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = CustomUserSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

