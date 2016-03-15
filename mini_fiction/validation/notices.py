#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation.utils import bool_coerce


NOTICE = {
    'name': {
        'type': 'string',
        'required': True,
        'minlength': 1,
        'maxlength': 64,
        'regex': r'^[A-z\_\-\.][A-z0-9\_\-\.]*$',
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
        'maxlength': 65535,
    },
    'is_template': {
        'type': 'boolean',
        'coerce': bool_coerce,
        'required': False,
        'default': False,
    },
    'show': {
        'type': 'boolean',
        'coerce': bool_coerce,
        'required': False,
        'default': False,
    },
}
