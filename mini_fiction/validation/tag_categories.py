#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext

from mini_fiction.validation.utils import safe_string_coerce, safe_string_multiline_coerce


TAG_CATEGORY = {
    'name': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': True,
        'minlength': 1,
        'maxlength': 255,
    },
    'color': {
        'type': 'string',
        'nullable': True,
        'regex': r'^(#([0-9A-Fa-f]{3}){1,2})?$',
        'error_messages': {
            'regex': lazy_gettext('Color format must be "#HHH" or "#HHHHHH"'),
        },
    },
    'description': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 4096,
    },
}
