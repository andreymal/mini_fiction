#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation.utils import bool_coerce, safe_string_coerce, safe_string_multiline_coerce


HTML_BLOCK = {
    'name': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': True,
        'minlength': 1,
        'maxlength': 64,
    },
    'lang': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': False,
        'minlength': 0,
        'maxlength': 6,
        'default': 'none',
    },
    'title': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': False,
        'default': '',
        'maxlength': 255,
    },
    'content': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
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
    'cache_time': {
        'type': 'integer',
        'coerce': int,
        'required': False,
        'default': 0,
        'min': 0,
        'max': 259200,
    }
}
