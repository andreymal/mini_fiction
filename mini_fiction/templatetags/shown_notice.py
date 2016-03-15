#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request

from mini_fiction.models import Notice
from mini_fiction.templatetags import registry


@registry.simple_tag()
def shown_notice():
    n = Notice.get(show=True)
    if not n:
        return
    last_id = request.cookies.get('last_notice')
    if last_id and last_id.isdigit() and int(last_id) >= n.id:
        return
    return n
