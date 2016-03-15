#!/usr/bin/env python3
# -*- coding: utf-8 -*-

STORY_COMMENT = {
    'parent': {
        'type': 'integer',
        'coerce': int,
        'default': 0,
    },

    'text': {
        'type': 'string',
        'required': True,
        'minlength': 1,
        'maxlength': 8192,
    },
}


NOTICE_COMMENT = {
    'parent': {
        'type': 'integer',
        'coerce': int,
        'default': 0,
    },

    'text': {
        'type': 'string',
        'required': True,
        'minlength': 1,
        'maxlength': 8192,
    },
}
