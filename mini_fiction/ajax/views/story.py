#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from pony.orm import db_session
from flask import Blueprint, current_app, request, jsonify, abort, render_template
from flask_login import current_user

from mini_fiction.ajax.utils import ajax_login_required
from mini_fiction.models import Story, Favorites, Bookmark


bp = Blueprint('ajax_story', __name__)


@bp.route('/<int:pk>/publish/', methods=('POST',))
@db_session
@ajax_login_required
def publish(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)

    user = current_user._get_current_object()
    if not user.is_staff and not story.editable_by(user):
        abort(403)

    if story.bl.publish(user, story.draft):  # draft == not published
        return str(pk)
    else:
        data = {
            'page_title': 'Неудачная попытка публикации',
            'story': story,
            'need_words': current_app.config['PUBLISH_SIZE_LIMIT']
        }
        return render_template('includes/ajax/story_ajax_publish_warning.html', **data)


@bp.route('/<int:pk>/approve/', methods=('POST',))
@db_session
@ajax_login_required
def approve(pk):
    user = current_user._get_current_object()
    if not user.is_staff:
        abort(403)  # TODO: refactor exceptions and move to bl
    story = Story.get(id=pk)
    if not story:
        abort(404)
    story.bl.approve(user, not story.approved)
    return jsonify({'success': True, 'story_id': story.id, 'approved': story.approved})


@bp.route('/<int:pk>/bookmark/', methods=('POST',))
@db_session
@ajax_login_required
def bookmark(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    user = current_user._get_current_object()
    b = story.bookmarks.select(lambda x: x.author == user).first()
    if b:
        b.delete()
    else:
        b = Bookmark(author=user, story=story)
    return str(pk)


@bp.route('/<int:pk>/favorite/', methods=('POST',))
@db_session
@ajax_login_required
def favorite(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    user = current_user._get_current_object()
    f = story.favorites.select(lambda x: x.author == user).first()
    if f:
        f.delete()
    else:
        f = Favorites(author=user, story=story)
    return str(pk)


@bp.route('/<int:pk>/vote/<int:value>/', methods=('POST',))
@db_session
@ajax_login_required
def vote(pk, value):
    user = current_user._get_current_object()
    story = Story.accessible(user).filter(lambda x: x.id == pk).first()
    if not story:
        abort(404)

    try:
        story.bl.vote(user, value, ip=request.remote_addr)
    except ValueError as exc:  # TODO: refactor exceptions
        return jsonify({'error': str(exc), 'success': False}), 403

    html = render_template('includes/story_header_info.html', story=story)
    return jsonify({'success': True, 'story_id': story.id, 'value': value, 'html': html})


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@ajax_login_required
def delete(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.deletable_by(current_user._get_current_object()):
        abort(403)

    if request.method == 'POST':
        story.bl.delete()
        return str(pk)

    return render_template('includes/ajax/story_ajax_confirm_delete.html', page_title='Подтверждение удаления рассказа', story=story)
