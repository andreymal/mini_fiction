#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps

from flask import render_template
from markupsafe import Markup

tags = {}


def simple_tag(name=None):
    def decorator(f):
        tags[name or f.__name__] = f
        return f
    return decorator


def inclusion_tag(template, name=None):
    def decorator(f):
        @wraps(f)
        def render_tag(*args, **kwargs):
            context = f(*args, **kwargs)
            return Markup(render_template(template, **context))
        tags[name or f.__name__] = render_tag
        return render_tag
    return decorator
