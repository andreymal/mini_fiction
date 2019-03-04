#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from flask_babel import lazy_gettext

from mini_fiction import models
from mini_fiction.validation.utils import bool_coerce, safe_string_coerce, safe_string_multiline_coerce


TAG = {
    'name': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'required': True,
        'minlength': 1,
        'maxlength': 255,
    },
    'category': {
        'type': 'integer',
        'coerce': lambda x: int(x) if x is not None else None,
        'nullable': True,
        'allowed_func': lambda: [None] + list(orm.select(x.id for x in models.TagCategory)),
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
        'coerce': (safe_string_multiline_coerce, 'strip'),
        'maxlength': 4096,
    },
    'is_main_tag': {
        'type': 'boolean',
        'coerce': bool_coerce,
    },
    'is_alias_for': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'maxlength': 255,
    },
    'is_hidden_alias': {
        'type': 'boolean',
        'coerce': bool_coerce,
    },
    'reason_to_blacklist': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'maxlength': 255,
    },
}
