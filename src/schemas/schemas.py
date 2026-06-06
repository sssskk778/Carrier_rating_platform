"""
Схемы валидации входных данных (Marshmallow).
Отвечают только за формат: типы, длины, допустимые значения.
Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import re
from marshmallow import Schema, fields, validate, validates, ValidationError
import math


class LoginSchema(Schema):
    """
    Валидация данных для входа в систему.
    Атрибуты:
        username — строка, обязательное, мин. 1 символ.
        password — строка, обязательное, мин. 1 символ.

    """
    username = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, validate=validate.Length(min=1))


class RegisterSchema(Schema):
    """
    Валидация данных для регистрации нового пользователя.
    Атрибуты:
        username  — строка, обязательное, от 3 до 100 символов.
        password  — строка, обязательное, минимум 6 символов.
        full_name — строка, обязательное, от 2 до 255 символов.
    Методы:
        validate_username — проверка формата имени (латиница, цифры, подчёркивание).
    """
    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=100, error='От 3 до 100 символов'),
    )
    password = fields.String(
        required=True,
        validate=validate.Length(min=6, error='Минимум 6 символов'),
    )
    full_name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=255, error='От 2 до 255 символов'),
    )

    @validates('username')
    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValidationError('Только латиница, цифры и подчёркивание')


class DatasetUploadSchema(Schema):
    """
    Валидация данных при загрузке набора данных.
    Атрибуты:
        name            — строка, необязательное, макс. 255 символов (по умолчанию '').
        description     — строка, необязательное, макс. 1000 символов (по умолчанию '').
        skip_preprocess — булево, необязательное (по умолчанию False).
    """
    name        = fields.String(load_default='', validate=validate.Length(max=255))
    description = fields.String(load_default='', validate=validate.Length(max=1000))
    skip_preprocess = fields.Boolean(load_default=False)


class ScenarioCreateSchema(Schema):
    """
    Валидация данных при создании нового сценария.
    Атрибуты:
        name          — строка, обязательное, от 3 до 255 символов.
        description   — строка, необязательное, макс. 1000 символов (по умолчанию '').
        method        — строка, обязательное, одно из: topsis, vikor.
        criterion_ids — список целых чисел, обязательное.
        swara_config  — словарь, необязательное (по умолчанию {}).
    """
    name = fields.String(
        required=True,
        validate=validate.Length(min=3, max=255, error='От 3 до 255 символов'),
    )
    description = fields.String(load_default='', validate=validate.Length(max=1000))
    method = fields.String(
        required=True,
        validate=validate.OneOf(['topsis', 'vikor'], error='Допустимые методы: topsis, vikor'),
    )
    criterion_ids = fields.List(fields.Integer(strict=True), required=True)
    swara_config  = fields.Dict(load_default={})


class ScenarioUpdateSchema(Schema):
    """
    Валидация данных при обновлении существующего сценария.
    Все поля необязательные — передаются только изменяемые.
    Атрибуты:
        name          — строка, необязательное, от 3 до 255 символов.
        description   — строка, необязательное, макс. 1000 символов.
        method        — строка, необязательное, одно из: topsis, vikor.
        criterion_ids — список целых чисел, необязательное.
        swara_config  — словарь, необязательное (по умолчанию {}).
    """
    name        = fields.String(validate=validate.Length(min=3, max=255, error='От 3 до 255 символов'))
    description = fields.String(validate=validate.Length(max=1000))
    method      = fields.String(validate=validate.OneOf(['topsis', 'vikor'], error='Допустимые методы: topsis, vikor'))
    criterion_ids = fields.List(fields.Integer(strict=True))
    swara_config  = fields.Dict(load_default={})


class SwaraWeightsSchema(Schema):
    """
    Валидация весовых коэффициентов для SWARA-метода.
    Атрибуты:
        ranking  — список строк, обязательное.
        s_values — список чисел с плавающей точкой, обязательное, каждое значение >= 0.
    Методы:
        validate_s_values_not_nan — проверка, что среди s_values нет NaN.
    """
    ranking = fields.List(fields.String(), required=True)
    s_values = fields.List(
        fields.Float(validate=validate.Range(min=0, error='Должно быть >= 0')),
        required=True,
    )

    @validates('s_values')
    def validate_s_values_not_nan(self, value):
        for v in value:
            if math.isnan(v):
                raise ValidationError('Значения не могут быть NaN')