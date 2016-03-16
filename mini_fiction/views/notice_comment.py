#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, abort, url_for
from pony.orm import db_session

from mini_fiction.models import Notice, NoticeComment
from mini_fiction.views import common_comment

bp = Blueprint('notice_comment', __name__)


@bp.route('/notice/<int:notice_id>/comment/add/', methods=('GET', 'POST'))
@db_session
def add(notice_id):
    notice = Notice.get(id=notice_id)
    if not notice:
        abort(404)

    # Все проверки доступа там
    return common_comment.add(
        'notice',
        notice,
        template='notices/comment_work.html',
    )


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(notice_id, local_id):
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.edit(
        'notice',
        comment,
        template='notices/comment_work.html',
    )


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(notice_id, local_id):
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.delete(
        'notice',
        comment,
        template='notices/comment_delete.html',
        template_ajax='notices/comment_delete_ajax.html',
        template_ajax_modal=True,
    )


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(notice_id, local_id):
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=True)
    if not comment:
        abort(404)

    return common_comment.restore(
        'notice',
        comment,
        template='notices/comment_restore.html',
        template_ajax='notices/comment_restore_ajax.html',
        template_ajax_modal=True,
    )


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/vote/', methods=('POST',))
@db_session
def vote(notice_id, local_id):
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.vote('notice', comment)


@bp.route('/ajax/notice/<int:notice_id>/comments/page/<int:page>/')
@db_session
def ajax(notice_id, page):
    notice = Notice.get(id=notice_id)
    if not notice:
        abort(404)

    per_page = current_app.config['COMMENTS_COUNT']['page']
    link = url_for('notices.show', name=notice.name, comments_page=page)

    return common_comment.ajax(
        'notice',
        notice,
        link,
        page,
        per_page,
        template_pagination='notices/comments_pagination.html',
    )


@bp.route('/ajax/notice/<int:notice_id>/comments/tree/<int:local_id>/')
@db_session
def ajax_tree(notice_id, local_id):
    notice = Notice.get(id=notice_id)
    if not notice:
        abort(404)

    comment = notice.comments.select(lambda x: x.local_id == local_id).first()
    if not comment:
        abort(404)

    return common_comment.ajax_tree(
        'notice',
        comment,
        target=notice,
    )
