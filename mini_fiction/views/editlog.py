#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import select, db_session
from flask_login import current_user, login_required
from flask_babel import gettext as _
from flask import Blueprint, current_app, abort, render_template, g, jsonify, request

from mini_fiction.models import Author, StoryLog, StoryContributor
from mini_fiction.utils.misc import Paginator, get_editlog_extra_info


bp = Blueprint('editlog', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@login_required
def index(page):
    user = current_user._get_current_object()

    view_args = {'page': page}

    if request.args.get('all') == '1':
        if not user.is_staff:
            abort(403)
        view_args['all'] = '1'
        queryset = StoryLog.select()
    else:
        queryset = StoryLog.select(
            lambda l: l.story in select(c.story for c in StoryContributor if c.user == user)
        )

    if request.args.get('staff') == '1':
        view_args['staff'] = '1'
        queryset = queryset.filter(lambda l: l.by_staff)

    # TODO: это довольно медленно, стоит оптимизировать
    if request.args.get('published') == '1':
        view_args['published'] = '1'
        queryset = queryset.filter(lambda l: l.story.approved and not l.story.draft)
    elif request.args.get('published') == '0':
        view_args['published'] = '0'
        queryset = queryset.filter(lambda l: not l.story.approved or l.story.draft)

    queryset = queryset.order_by(StoryLog.created_at.desc()).prefetch(StoryLog.story, StoryLog.user)

    page_obj = Paginator(
        page, queryset.count(),
        per_page=current_app.config.get('EDIT_LOGS_PER_PAGE', 100),
        view_args=view_args,
    )

    edit_log = page_obj.slice_or_404(queryset)

    return render_template(
        'story_edit_log.html',
        edit_log=edit_log,
        edit_log_users=load_users_for_editlog(edit_log),
        page_obj=page_obj,
        page_title=_('Edit log'),
        view_args=view_args,
        filter_all=view_args.get('all') == '1',
        filter_staff=view_args.get('staff') == '1',
        filter_published=view_args.get('published'),
    )


@bp.route('/<int:editlog_id>/')
@db_session
def show(editlog_id):
    edit_log = StoryLog.select(lambda x: x.id == editlog_id).prefetch(StoryLog.story, StoryLog.user).first()
    if not edit_log:
        abort(404)
    if not edit_log.story.bl.can_view_editlog(current_user._get_current_object()):
        abort(403)

    extra = get_editlog_extra_info(edit_log, prepare_chapter_diff=True, show_newlines=True)

    data = {
        'page_title': _('Edit log'),
        'item': edit_log,
        'edit_log_users': load_users_for_editlog([edit_log]),
        'extra': extra,
    }

    if g.is_ajax:
        html = render_template('story_edit_log_show_modal.html', **data)
        return jsonify({'page_content': {'modal': html}})
    return render_template('story_edit_log_show.html', **data)


def load_users_for_editlog(edit_log):
    user_ids = set()
    for item in edit_log:
        user_ids.add(item.user.id)
        item_data = item.data
        if 'contributors' in item_data:
            for v in item_data['contributors']:
                user_ids |= {x['user'] for x in v}
    edit_log_users = {x.id: x for x in Author.select(lambda x: x.id in user_ids)}
    return edit_log_users
