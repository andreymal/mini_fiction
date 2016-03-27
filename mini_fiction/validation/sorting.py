#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext


CATEGORY = {
    'name': {
        'type': 'string',
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'description': {
        'type': 'string',
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
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'description': {
        'type': 'string',
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
        'required': True,
        'minlength': 1,
        'maxlength': 256,
    },
    'description': {
        'type': 'string',
        'required': False,
        'default': '',
        'minlength': 0,
        'maxlength': 65535,
    },
}
