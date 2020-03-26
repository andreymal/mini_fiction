#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app, g

from mini_fiction.utils.misc import sitename, emailsitename


context_processors = []


def context_processor(func):
    context_processors.append(func)
    return func


@context_processor
def website_settings():
    result = {
        'SITE_NAME': sitename(),
        'EMAIL_SITE_NAME': emailsitename(),
        'STATIC_V': current_app.static_v,
        'base': current_app.jinja_env.get_template('base.json' if getattr(g, 'is_ajax', False) else 'base.html'),
        'contact_types': {x['name']: x for x in current_app.config['CONTACTS']},
        'extra_css': current_app.extra_css,
        'extra_js': current_app.extra_js,
    }

    for k in [
        'SERVER_NAME',
        'PREFERRED_URL_SCHEME',
        'DEFAULT_DATE_FORMAT',
        'DEFAULT_DATETIME_FORMAT',
        'DEFAULT_TIME_FORMAT',
    ]:
        result[k] = current_app.config[k]

    return result
