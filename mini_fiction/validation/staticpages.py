#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation.utils import bool_coerce


STATIC_PAGE = {
    'name': {
        'type': 'string',
        'required': True,
        'minlength': 1,
        'maxlength': 64,
        'regex': r'^[A-z0-9\_\-\.][A-z0-9\_\-\.\/]*[A-z0-9\_\-\.]$',
    },
    'lang': {
        'type': 'string',
        'required': False,
        'minlength': 0,
        'maxlength': 6,
        'default': 'none',
    },
    'title': {
        'type': 'string',
        'required': False,
        'minlength': 0,
        'maxlength': 192,
        'default': '',
    },
    'content': {
        'type': 'string',
        'required': True,
        'minlength': 0,
        'maxlength': 1048575,
    },
    'is_template': {
        'type': 'boolean',
        'coerce': bool_coerce,
        'required': False,
        'default': False,
    },
    'is_full_page': {
        'type': 'boolean',
        'coerce': bool_coerce,
        'required': False,
        'default': False,
    },
}
