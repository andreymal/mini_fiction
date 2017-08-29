#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app, g

from mini_fiction.utils.misc import sitename


context_processors = []


def context_processor(func):
    context_processors.append(func)
    return func


@context_processor
def website_settings():
    result = {
        'SITE_NAME': sitename(),
        'SERVER_NAME': current_app.config['SERVER_NAME'],
        'PREFERRED_URL_SCHEME': current_app.config['PREFERRED_URL_SCHEME'],
        'base': current_app.jinja_env.get_template('base.json' if getattr(g, 'is_ajax', False) else 'base.html'),
        'contact_types': {x['name']: x for x in current_app.config['CONTACTS']},
    }
    return result
