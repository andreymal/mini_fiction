#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm

from mini_fiction import models
from mini_fiction.validation.utils import bool_coerce


STORY = {
    'title': {
        'type': 'string',
        'required': True,
        'minlength': 1,
        'maxlength': 512,
        'error_messages': {
            'minlength': 'Пожалуйста, назовите ваш рассказ',
            'required': 'Пожалуйста, назовите ваш рассказ',
        },
    },
    'categories': {
        'type': 'list',
        'required': True,
        'minlength': 1,
        'schema': {
            'type': 'integer',
            'coerce': int,
            'allowed_func': lambda: orm.select(x.id for x in models.Category)[:],
        },
        'error_messages': {
            'required': 'Жанры - обязательное поле',
            'minlength': 'Жанры - обязательное поле',
        },
    },
    'characters': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'integer',
            'coerce': int,
            'allowed_func': lambda: orm.select(x.id for x in models.Character)[:],
        },
    },
    'summary': {
        'type': 'string',
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
        'default': '',
        'maxlength': 4096,
    },
    'rating': {
        'type': 'integer',
        'required': True,
        'coerce': int,
        'allowed_func': lambda: orm.select(x.id for x in models.Rating)[:],
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
    'freezed': {
        'type': 'boolean',
        'required': True,
        'coerce': bool_coerce,
        'error_messages': {
            'required': 'Нужно обязательно указать статус рассказа!',
        },
    },
    'finished': {
        'type': 'boolean',
        'required': True,
        'coerce': bool_coerce,
        'error_messages': {
            'required': 'Нужно обязательно указать статус рассказа!',
        },
    },
    'classifications': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'integer',
            'coerce': int,
            'allowed_func': lambda: orm.select(x.id for x in models.Classifier)[:],
        },
    },
}
