#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation.utils import bool_coerce, safe_string_coerce, safe_string_multiline_coerce


LOGOPIC = {
    'picture': {
        'type': 'file',
        'required': True,
    },
    'visible': {
        'type': 'boolean',
        'coerce': bool_coerce,
        'required': False,
        'default': True,
    },
    'description': {
        'type': 'string',
        'coerce': safe_string_multiline_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 65535,
    },
    'original_link': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 255,
    },
    'original_link_label': {
        'type': 'string',
        'coerce': safe_string_coerce,
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 4096,
    },
}


LOGOPIC_FOR_UPDATE = dict(LOGOPIC)
LOGOPIC_FOR_UPDATE['picture'] = {
    'type': 'file',
    'nullable': True,
    'default': None,
}
