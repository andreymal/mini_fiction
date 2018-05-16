#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation.utils import safe_string_multiline_coerce, strip_string_coerce


STORY_COMMENT = {
    'parent': {
        'type': 'integer',
        'coerce': int,
        'default': 0,
    },

    'text': {
        'type': 'string',
        'coerce': (safe_string_multiline_coerce, strip_string_coerce),
        'required': True,
        'minlength': 1,
        'maxlength': 8192,
    },
}


NEWS_COMMENT = {
    'parent': {
        'type': 'integer',
        'coerce': int,
        'default': 0,
    },

    'text': {
        'type': 'string',
        'coerce': (safe_string_multiline_coerce, strip_string_coerce),
        'required': True,
        'minlength': 1,
        'maxlength': 8192,
    },
}
