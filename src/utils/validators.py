"""
Модуль декораторов валидации запросов.

Автор: Лосева Е.А.
Дата создания: ДД.ММ.ГГГГ
Последнее изменение: ДД.ММ.ГГГГ
Контакт: ekaterinaloseva91@gmail.com
"""
from functools import wraps
from flask import request, jsonify
from marshmallow import ValidationError


def _first_error(messages: dict) -> str:
    """Достаёт первое читаемое сообщение об ошибке из словаря Marshmallow."""
    for field, errors in messages.items():
        if isinstance(errors, list) and errors:
            return errors[0]
        if isinstance(errors, dict):
            result = _first_error(errors)
            if result:
                return result
    return 'Проверьте правильность заполнения полей'


def validate_body(schema_cls):
    """Декоратор: валидирует JSON-тело запроса через Marshmallow-схему."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = schema_cls().load(request.get_json(silent=True) or {})
            except ValidationError as e:
                return jsonify({'ok': False, 'error': _first_error(e.messages)}), 422
            return f(*args, data=data, **kwargs)
        return wrapper
    return decorator
