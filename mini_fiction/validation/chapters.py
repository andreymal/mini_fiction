#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation.utils import safe_string_coerce, safe_string_multiline_coerce, bool_coerce


CHAPTER = {
    'title': {
        'type': 'string',
        'coerce': (safe_string_coerce, 'strip'),
        'required': False,
        'default': '',
        'maxlength': 512,
    },
    'notes': {
        'type': 'string',
        'coerce': (safe_string_multiline_coerce, 'strip'),
        'required': False,
        'default': '',
        'maxlength': 4096,
    },
    'text': {
        'type': 'string',
        'coerce': (safe_string_multiline_coerce, 'strip'),
        'required': False,
        'default': '',
        'maxlength': 1000000,
    },
}

CHAPTER_FORM = {
    'publication_status': {
        'type': 'string',
        'required': False,
        'default': 'draft',
        'allowed': ['publish', 'publish_all', 'draft'],
    },
    'minor': {
        'type': 'boolean',
        'coerce': bool_coerce,
        'required': False,
        'default': False,
    },
}

CHAPTER_FORM.update(CHAPTER)
