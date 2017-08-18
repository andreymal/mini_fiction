#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request, url_for

from mini_fiction.templatetags import registry
from mini_fiction.utils import misc as utils_misc


@registry.simple_tag()
def is_current_endpoint(endpoint, **kwargs):
    if not endpoint or endpoint != request.endpoint:
        return False
    if kwargs and not request.view_args:
        return False
    for k in kwargs:
        if k not in request.view_args or request.view_args[k] != kwargs[k]:
            return False
    return True


@registry.simple_tag()
def prepare_editlog(edit_log):
    log_data = []

    for log_item in edit_log:
        log_data.append((log_item, utils_misc.get_editlog_extra_info(log_item)))

    return log_data


@registry.simple_tag()
def modified_url(endpoint=None, view_args=None, **kwargs):
    endpoint = endpoint or request.endpoint
    view_args = view_args if view_args is not None else dict(request.view_args or {})
    view_args.update(kwargs)
    return url_for(endpoint, **view_args)
