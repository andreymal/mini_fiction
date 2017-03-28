#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import db_session
from flask_login import current_user
from flask_babel import gettext as _
from flask import Blueprint, current_app, abort, render_template, g, jsonify

from mini_fiction.models import StoryLog
from mini_fiction.utils.views import paginate_view
from mini_fiction.utils.misc import get_editlog_extra_info


bp = Blueprint('editlog', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    if not current_user.is_staff:
        abort(403)

    objects = StoryLog.select(lambda x: x.by_staff).order_by(StoryLog.created_at.desc()).prefetch(StoryLog.story)
    return paginate_view(
        'story_edit_log.html',
        objects,
        count=objects.count(),
        page_title=_('Moderation log'),
        objlistname='edit_log',
        per_page=current_app.config.get('EDIT_LOGS_PER_PAGE', 100),
    )


@bp.route('/<int:editlog_id>/')
@db_session
def show(editlog_id):
    if not current_user.is_staff:
        abort(403)

    edit_log = StoryLog.select(lambda x: x.id ==editlog_id).prefetch(StoryLog.story).first()
    if not edit_log:
        abort(404)

    extra = get_editlog_extra_info(edit_log, prepare_chapter_diff=True)

    data = {
        'page_title': _('Moderation log'),
        'item': edit_log,
        'extra': extra,
    }

    if g.is_ajax:
        html = render_template('story_edit_log_show_modal.html', **data)
        return jsonify({'page_content': {'modal': html}})
    return render_template('story_edit_log_show.html', **data)
