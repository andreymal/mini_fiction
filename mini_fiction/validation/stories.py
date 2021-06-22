#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm

from mini_fiction import models
from mini_fiction.validation.utils import bool_coerce, safe_string_coerce, safe_string_multiline_coerce


STORY = {
    'title': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'required': True,
        'minlength': 1,
        'maxlength': 512,
        'error_messages': {
            'minlength': 'Пожалуйста, назовите ваш рассказ',
            'required': 'Пожалуйста, назовите ваш рассказ',
        },
    },
    'tags': {
        'type': 'list',
        'required': True,
        'minlength': 1,
        'schema': {
            'type': 'string',
            'coerce': str,
        },
        'error_messages': {
            'required': 'Укажите хотя бы один тег',
            'minlength': 'Укажите хотя бы один тег',
        },
    },
    'characters': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'integer',
            'coerce': int,
            'allowed_func': lambda: list(orm.select(x.id for x in models.Character)),
        },
    },
    'summary': {
        'type': 'string',
        'coerce': (safe_string_multiline_coerce, 'strip'),
        'required': True,
        'minlength': 1,
        'maxlength': 4096,
        'error_messages': {
            'minlength': 'Опишите вкратце содержание рассказа - это обязательное поле',
            'required': 'Опишите вкратце содержание рассказа - это обязательное поле',
        },
    },
    'notes': {
        'type': 'string',
        'coerce': (safe_string_multiline_coerce, 'strip'),
        'default': '',
        'maxlength': 4096,
    },
    'original_url': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 255,
        'regex': r'^(https?://[^\/\ \?]+\.[^\/\ \?]+(/[^ ]*)?)?$',
        'error_messages': {
            'regex': 'Это не очень похоже на ссылку',
        },
    },
    'original_title': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 255,
    },
    'original_author': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 255,
    },
    'rating': {
        'type': 'integer',
        'required': True,
        'coerce': int,
        'allowed_func': lambda: list(orm.select(x.id for x in models.Rating)),
        'error_messages': {
            'required': 'Нужно обязательно указать рейтинг рассказа!',
        },
    },
    'original': {
        'type': 'boolean',
        'required': True,
        'coerce': bool_coerce,
        'error_messages': {
            'required': 'Нужно обязательно указать состояние рассказа!',
        },
    },
    'status': {
        'type': 'string',
        'required': True,
        'allowed': ['unfinished', 'finished', 'freezed'],
        'error_messages': {
            'required': 'Нужно обязательно указать статус рассказа!',
        },
    },
}
