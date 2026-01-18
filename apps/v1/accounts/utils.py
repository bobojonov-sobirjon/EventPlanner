import os
import hashlib
import hmac
import time
import urllib.parse
import json
from typing import Dict, Optional
from django.conf import settings


TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN', ''))


def check_auth(init_data, bot_token):
    """
    Проверка аутентификации Telegram Web App данных
    
    Args:
        init_data: Словарь с распарсенными данными initData
        bot_token: Токен Telegram бота
        
    Returns:
        bool: True если данные валидны, False в противном случае
    """
    hash_received = init_data.get("hash", "")
    if not hash_received:
        return False

    data_check = []
    for key, value in init_data.items():
        if key == "hash":
            continue
        if isinstance(value, list):
            data_check.append((key, value[0]))
        else:
            data_check.append((key, value))

    data_check.sort(key=lambda x: x[0])
    auth_str = "\n".join([f"{k}={v}" for k, v in data_check])

    secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()

    hash_calculated = hmac.new(secret_key, auth_str.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(hash_calculated, hash_received):
        return False

    auth_date = int(init_data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return False

    return True


def verify_telegram_webapp_data(init_data: str, bot_token: str, max_age: int = 86400) -> bool:
    """
    Проверка данных Telegram Web App initData
    
    Args:
        init_data: Строка initData из Telegram Web App
        bot_token: Токен вашего Telegram бота
        max_age: Максимальный возраст данных в секундах (по умолчанию 24 часа)
        
    Returns:
        bool: True если данные валидны, False в противном случае
    """
    try:
        import time
        
        parsed_data = urllib.parse.parse_qs(init_data)
        
        if 'hash' not in parsed_data:
            return False
        
        received_hash = parsed_data['hash'][0]
        
        if 'auth_date' in parsed_data:
            auth_date = int(parsed_data['auth_date'][0])
            current_time = int(time.time())
            if current_time - auth_date > max_age:
                return False
        
        data_pairs = []
        for key, value in parsed_data.items():
            if key != 'hash':
                data_pairs.append(f"{key}={value[0]}")
        
        data_pairs.sort()
        data_check_string = '\n'.join(data_pairs)
        
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == received_hash
    except Exception:
        return False


def parse_telegram_user_data(init_data: str) -> Optional[Dict]:
    """
    Парсинг данных пользователя из Telegram initData
    
    Args:
        init_data: Строка initData из Telegram Web App
        
    Returns:
        dict: Распарсенные данные пользователя или None
    """
    try:
        parsed_data = urllib.parse.parse_qs(init_data)
        
        if 'user' not in parsed_data:
            return None
        
        import json
        user_data = json.loads(parsed_data['user'][0])
        
        return {
            'telegram_id': user_data.get('id'),
            'telegram_username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'photo_url': user_data.get('photo_url'),
            'language_code': user_data.get('language_code'),
        }
    except Exception:
        return None
