#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_login import current_user

from mini_fiction.templatetags import registry
from mini_fiction.utils.misc import calc_comment_threshold


@registry.simple_tag()
def get_comment_threshold():
    return calc_comment_threshold(current_user)
