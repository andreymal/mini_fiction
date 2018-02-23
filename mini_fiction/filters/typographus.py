#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .base import html_text_transform


typo_patterns = [
    (r'(^|\n)[-—]-?[ \t\r\f\v]+', '\\1— '),
    (r'[ \t\r\f\v]+[-—]-?[ \t\r\f\v]+', '\xa0— '),
]
typo_patterns = [(re.compile(p), r) for p, r in typo_patterns]


@html_text_transform
def typo(text):
    for p, r in typo_patterns:
        text = p.subn(r, text)[0]  # pylint: disable=no-member
    return text
