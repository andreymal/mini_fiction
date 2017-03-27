#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import pgettext as pgettext_orig

from mini_fiction.templatetags import registry


@registry.simple_tag()
def pgettext(context, string, **variables):
    return pgettext_orig(context, string, **variables)
