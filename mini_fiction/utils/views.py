#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps
from typing import Any, Collection, Dict

from pony import orm
from flask import request, render_template, abort
from flask_login import current_user

from mini_fiction import models
from mini_fiction.utils.misc import Paginator


def paginate_view(template, objlist, page=None, objlistname='objects', endpoint=None, view_args=None, per_page=50, extra_context=None, **kwargs):
    # legacy
    data = dict(kwargs)
    if 'count' in data:
        count = data.pop('count')
    else:
        count = len(objlist)

    if view_args is None:
        view_args = dict(request.view_args or {})

    if page is None:
        page = view_args.pop('page')

    page_obj = Paginator(page, count, per_page=per_page)
    page_objlist = page_obj.slice(objlist)
    # page_objlist = objlist[0:2]
    if not page_objlist and page != 1:
        abort(404)

    data.update({
        'endpoint': endpoint or request.endpoint,
        'view_args': view_args,
        'page_obj': page_obj,
    })
    if extra_context:
        data.update(extra_context(page_objlist, page_obj) or {})
    data[objlistname] = page_objlist

    return render_template(template, **data)


def cached_lists(
    story_ids: Collection[int],
    *,
    unread_chapters_count: bool = True,
    unread_comments_count: bool = True,
    chapter_view_dates: bool = False,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if not current_user.is_authenticated:
        data.update({
            'favorited_ids': [],
            'bookmarked_ids': [],
        })
        if unread_chapters_count:
            data['unread_chapters_count'] = {x: 0 for x in story_ids}
        if unread_comments_count:
            data['unread_comments_count'] = {x: 0 for x in story_ids}
        if chapter_view_dates:
            data['chapter_view_dates'] = {}
    else:
        data.update({
            'favorited_ids': list(orm.select(x.story.id for x in models.Favorites if x.author == current_user and x.story.id in story_ids)),
            'bookmarked_ids': list(orm.select(x.story.id for x in models.Bookmark if x.author == current_user and x.story.id in story_ids)),
        })
        if unread_chapters_count:
            data['unread_chapters_count'] = models.Story.bl.get_unread_chapters_count(current_user, story_ids)
        if unread_comments_count:
            data['unread_comments_count'] = models.Story.bl.get_unread_comments_count(current_user, story_ids)
        if chapter_view_dates:
            viewed_chapters = models.StoryView.select(lambda x: x.author == current_user and x.story.id in story_ids)
            data['chapter_view_dates'] = {x.chapter.id: x.date for x in viewed_chapters if x.chapter}
    return data


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_staff:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def admin_sort(sorting, objects, fields_map, default='id'):
    desc = False
    if sorting and sorting.startswith('-'):
        desc = True
        sorting = sorting[1:]

    if sorting in fields_map:
        fields = fields_map[sorting]
    else:
        desc = False
        if default.startswith('-'):
            desc = True
            default = default[1:]
        fields = fields_map[default]

    if not isinstance(fields, (tuple, list)):
        fields = [fields]

    if not desc:
        return objects.order_by(*fields)
    return objects.order_by(*[orm.desc(x) for x in fields])
