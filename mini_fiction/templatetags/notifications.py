#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.templatetags import registry

from flask_login import current_user


@registry.simple_tag()
def get_unread_notifications_count():
    if not current_user.is_authenticated:
        return 0
    return current_user.bl.get_unread_notifications_count()
