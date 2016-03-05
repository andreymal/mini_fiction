#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random

from flask import current_app, url_for

from mini_fiction.templatetags import registry


@registry.simple_tag()
def random_logo():
    logos = current_app.config.get('RANDOM_LOGOS')
    if not logos:
        return url_for('static', filename='i/logopics/logopic-5.jpg')
    logo = dict(random.Random(int(time.time()) // 3600).choice(logos))
    if 'endpoint' in logo:
        return url_for(logo.pop('endpoint'), **logo)
    else:
        return logo['url']
