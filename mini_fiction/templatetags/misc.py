#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request
from flask_babel import pgettext

from mini_fiction.templatetags import registry


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

    # Подсчитываем для шаблона, как красиво вывести изменения
    for log_item in edit_log:
        log_extra_item = {'list_items': False, 'label': pgettext('story_edit_log', 'edited story')}
        edited_data = log_item.data

        if len(edited_data) == 1:
            if 'draft' in edited_data and edited_data['draft'][1] is True:
                log_extra_item['label'] = pgettext('story_edit_log', 'published story')
            elif 'draft' in edited_data and edited_data['draft'][1] is False:
                log_extra_item['label'] = pgettext('story_edit_log', 'sent to drafts story')
            elif 'approved' in edited_data and edited_data['approved'][1] is True:
                log_extra_item['label'] = pgettext('story_edit_log', 'approved story')
            elif 'approved' in edited_data and edited_data['approved'][1] is False:
                log_extra_item['label'] = pgettext('story_edit_log', 'unapproved story')
            else:
                log_extra_item['list_items'] = True
        else:
            log_extra_item['list_items'] = True

        log_data.append((log_item, log_extra_item))

    return log_data
