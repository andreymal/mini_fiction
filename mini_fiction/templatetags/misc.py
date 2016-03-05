#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request

from mini_fiction.templatetags import registry


@registry.simple_tag()
def is_current_endpoint(endpoint, **kwargs):
    if not endpoint or endpoint != request.endpoint:
        return False
    if kwargs and not request.view_args:
        return False
    for k in kwargs:
        if k not in request.view_args or request.view_args[k] != kwargs[k]:
            return False
    return True
