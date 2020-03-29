#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.utils import timesince as utils_timesince
from mini_fiction.templatefilters.registry import register_tag


@register_tag()
def timesince(dt=None):
    return utils_timesince.timesince(dt)
