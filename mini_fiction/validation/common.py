#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app

from mini_fiction.validation.utils import safe_string_coerce


USERNAME = {
    'type': 'string',
    'minlength': 2,
    'maxlength': 32,
    'coerce': [safe_string_coerce, 'strip'],
    'dynregex': lambda: current_app.config['USERNAME_REGEX'],
    'error_messages': {
        'dynregex': lambda: current_app.config['USERNAME_ERROR_MESSAGE'],
    },
}


PASSWORD = {
    'type': 'string',
    'minlength': 6,
    'maxlength': 32,
}


EMAIL = {
    'type': 'string',
    'minlength': 6,
    'maxlength': 75,
    'coerce': [safe_string_coerce, 'strip'],
    'regex': r'^.+@([^.@][^@]+)$',
    'error_messages': {
        'regex': 'Пожалуйста, исправьте ошибку в адресе e-mail: похоже, он неправильный',
    },
}
