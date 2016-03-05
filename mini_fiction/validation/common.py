#!/usr/bin/env python3
# -*- coding: utf-8 -*-

USERNAME = {
    'type': 'string',
    'minlength': 2,
    'maxlength': 32,
    'regex': r'^[0-9a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u0401_@+-.. ]+$',
    'error_messages': {
        'any': 'Пожалуйста, исправьте ошибку в логине - '
            'он может содержать только русские/латинские буквы, цифры, пробел, '
            'точку и символы _ @ + -',
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
    'regex': r'^.+@([^.@][^@]+)$',
    'error_messages': {
        'regex': 'Пожалуйста, исправьте ошибку в адресе e-mail: похоже, он неправильный',
    },
}
