#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import pgettext as pgettext_orig

from mini_fiction.templatetags import registry
from mini_fiction.utils import timezone


@registry.simple_tag()
def pgettext(context, string, **variables):
    return pgettext_orig(context, string, **variables)


@registry.simple_tag()
def get_timezone_info(tzname):
    return timezone.get_timezone_info(tzname)


@registry.simple_tag()
def get_timezone_infos():
    return timezone.get_timezone_infos()
