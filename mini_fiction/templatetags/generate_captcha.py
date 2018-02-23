#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app

from mini_fiction.templatetags import registry


@registry.simple_tag()
def generate_captcha():
    if not current_app.captcha:
        return {'cls': None}

    return current_app.captcha.generate()
