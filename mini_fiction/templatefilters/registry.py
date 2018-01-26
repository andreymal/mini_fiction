#!/usr/bin/env python3
# -*- coding: utf-8 -*-

filters = {}


def register_tag(name=None):
    def decorator(f):
        filters[name or f.__name__] = f
        return f
    return decorator
