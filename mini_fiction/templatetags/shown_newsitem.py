#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request

from mini_fiction.models import NewsItem
from mini_fiction.templatetags import registry


@registry.simple_tag()
def shown_newsitem():
    n = NewsItem.get(show=True)
    if not n:
        return
    last_id = request.cookies.get('last_newsitem')
    if last_id and last_id.isdigit() and int(last_id) == n.id:
        return
    return n
