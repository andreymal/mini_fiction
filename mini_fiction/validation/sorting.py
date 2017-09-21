#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext

from mini_fiction.validation.utils import safe_string_coerce, safe_string_multiline_coerce


CATEGORY = {
    'name': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'description': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 65535,
    },
    'color': {
        'type': 'string',
        'required': True,
        'regex': r'^#([0-9A-Fa-f]{3}){1,2}$',
        'error_messages': {
            'regex': lazy_gettext('Color format must be "#HHH" or "#HHHHHH"'),
        },
    },
}


CHARACTER = {
    'name': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'picture': {
        'type': 'file',
        'required': True,
    },
    'description': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 65535,
    },
    'group': {
        'type': 'integer',
        'required': True,
        'coerce': int,
    },
}


CHARACTER_GROUP = {
    'name': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'description': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 65535,
    },
}


CLASSIFIER = {
    'name': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'description': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 65535,
    },
}
