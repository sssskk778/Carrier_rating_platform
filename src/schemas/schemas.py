"""
Схемы валидации входных данных (Marshmallow).
Отвечают только за формат: типы, длины, допустимые значения.
"""
import re
from marshmallow import Schema, fields, validate, validates, ValidationError
import math


class LoginSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, validate=validate.Length(min=1))


class RegisterSchema(Schema):
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
    name        = fields.String(load_default='', validate=validate.Length(max=255))
    description = fields.String(load_default='', validate=validate.Length(max=1000))
    skip_preprocess = fields.Boolean(load_default=False)


class ScenarioCreateSchema(Schema):
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
    name        = fields.String(validate=validate.Length(min=3, max=255, error='От 3 до 255 символов'))
    description = fields.String(validate=validate.Length(max=1000))
    method      = fields.String(validate=validate.OneOf(['topsis', 'vikor'], error='Допустимые методы: topsis, vikor'))
    criterion_ids = fields.List(fields.Integer(strict=True))
    swara_config  = fields.Dict(load_default={})


class SwaraWeightsSchema(Schema):
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