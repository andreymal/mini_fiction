#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .base import html_text_transform


typo_patterns = [
    (r'(^|\n)(<[^>]+?>)?[-—]-?[ \t\r\f\v]+', '\\1\\2— '),
    (r'[ \t\r\f\v]+[-—]-?[ \t\r\f\v]+', '\xa0— '),
]
typo_patterns = [(re.compile(p_), r_) for p_, r_ in typo_patterns]


@html_text_transform
def typo(text):
    for p, r in typo_patterns:
        text = p.subn(r, text)[0]
    return text
