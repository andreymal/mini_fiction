#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import g

from mini_fiction.models import Logopic
from mini_fiction.templatetags import registry


@registry.simple_tag()
def get_current_logopic():
    logo = Logopic.bl.get_current()
    if logo:
        if g.locale.language in logo['original_link_label']:
            logo['original_link_label'] = logo['original_link_label'][g.locale.language]
        else:
            logo['original_link_label'] = logo['original_link_label'].get('') or ''
    return logo
