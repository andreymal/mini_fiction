#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Markup, escape, request, url_for

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
    view_args = dict(view_args) if view_args is not None else dict(request.view_args or {})
    view_args.update(kwargs)
    return url_for(endpoint, **view_args)


@registry.simple_tag()
def admin_sorting_link(label, sorting_asc, sorting_desc=None, endpoint=None, view_args=None, **kwargs):
    endpoint = endpoint or request.endpoint
    view_args = dict(view_args) if view_args is not None else dict(request.view_args or {})
    view_args.update(kwargs)

    if sorting_desc is None:
        sorting_desc = '-' + sorting_asc

    sorting = view_args.get('sorting')

    if not sorting or sorting != sorting_asc:
        view_args['sorting'] = sorting_asc
    else:
        view_args['sorting'] = sorting_desc

    if sorting == sorting_asc:
        order_arrow = ' ↑'
    elif sorting == sorting_desc:
        order_arrow = ' ↓'
    else:
        order_arrow = ''

    return Markup('<a href="{url}" class="td-sortable-link">{label}{order_arrow}</a>'.format(
        url=escape(url_for(endpoint, **view_args)),
        label=escape(label),
        order_arrow=order_arrow,
    ))


@registry.simple_tag()
def safe_password_hash(password_hash):
    try:
        if password_hash.startswith('$pbkdf2$pbkdf2_sha256$'):
            prefix1, prefix2, algorithm, iterations, salt, result = password_hash[:].split('$', 5)
            return '$'.join([
                prefix1, prefix2, algorithm, iterations,
                salt[:4] + '*' * (len(salt) - 4),
                result[:6] + '*' * (len(result) - 6),
            ])

        if password_hash.startswith('$bcrypt$$') and password_hash.count('$') == 5:
            prefix, data = password_hash.rsplit('$', 1)
            return prefix + '$' + data[:6] + '*' * (len(data) - 6)

    except Exception:
        pass

    if len(password_hash) < 12:
        return '*' * len(password_hash)

    return password_hash[:4] + '*' * (len(password_hash) - 4)
