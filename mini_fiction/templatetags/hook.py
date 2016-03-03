#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Markup, current_app

from mini_fiction.templatetags import registry


@registry.simple_tag()
def hook(name, *args, **kwargs):
    funcs = current_app.hooks.get(name, ())
    result = ''.join(f(*args, **kwargs) for f in funcs)
    return Markup(result)
