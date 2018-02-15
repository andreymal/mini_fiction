#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app, url_for, g

from mini_fiction.utils.misc import sitename, emailsitename


context_processors = []


def context_processor(func):
    context_processors.append(func)
    return func


@context_processor
def website_settings():
    loading_icon = dict(current_app.config['LOADING_ICON'])
    loading_icon = url_for(loading_icon.pop('endpoint'), **loading_icon)

    result = {
        'SITE_NAME': sitename(),
        'EMAIL_SITE_NAME': emailsitename(),
        'SERVER_NAME': current_app.config['SERVER_NAME'],
        'PREFERRED_URL_SCHEME': current_app.config['PREFERRED_URL_SCHEME'],
        'STATIC_V': current_app.static_v,
        'LOADING_ICON': loading_icon,
        'base': current_app.jinja_env.get_template('base.json' if getattr(g, 'is_ajax', False) else 'base.html'),
        'contact_types': {x['name']: x for x in current_app.config['CONTACTS']},
        'extra_css': current_app.extra_css,
        'extra_js': current_app.extra_js,
    }
    return result
