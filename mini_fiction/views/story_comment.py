#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for, g, jsonify
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Story, StoryComment, CoAuthorsStory
from mini_fiction.utils.misc import Paginator
from mini_fiction.validation import ValidationError

bp = Blueprint('story_comment', __name__)


@bp.route('/story/<int:story_id>/comment/add/', methods=('GET', 'POST'))
@db_session
def add(story_id):
    user = current_user._get_current_object()
    story = Story.get(id=story_id)
    if not story:
        abort(404)

    if request.args.get('parent') and request.args['parent'].isdigit():
        parent = StoryComment.get(story=story_id, local_id=int(request.args['parent']), deleted=False)
        if not parent:
            abort(404)
    else:
        parent = None

    if parent and not parent.bl.can_answer_by(user):
        abort(403)
    elif not story.bl.can_comment_by(user):
        abort(403)

    form = CommentForm(request.form)
    if form.validate_on_submit():
        data = dict(form.data)
        if request.form.get('parent'):
            data['parent'] = request.form['parent']
        try:
            comment = StoryComment.bl.create(story, user, request.remote_addr, data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Add new comment'),
        'form': form,
        'story': story,
        'parent_comment': parent,
        'edit': False,
    }
    return render_template('story_comment_work.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(story_id, local_id):
    user = current_user._get_current_object()
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)
    if not comment.bl.can_update_by(user):
        abort(403)

    form = CommentForm(request.form, data={'text': comment.text})
    if form.validate_on_submit():
        try:
            comment.bl.update(user, request.remote_addr, form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Edit comment'),
        'form': form,
        'story': comment.story,
        'comment': comment,
        'edit': True,
    }
    return render_template('story_comment_work.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(story_id, local_id):
    user = current_user._get_current_object()
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)
    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.delete(user)
        return redirect(comment.bl.get_permalink())
    data = {
        'page_title': gettext('Confirm delete comment'),
        'story': comment.story,
        'comment': comment,
    }
    return render_template('story_comment_delete.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(story_id, local_id):
    user = current_user._get_current_object()
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=True)
    if not comment:
        abort(404)
    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.restore(user)
        return redirect(comment.bl.get_permalink())
    data = {
        'page_title': gettext('Confirm restore comment'),
        'story': comment.story,
        'comment': comment,
    }
    return render_template('story_comment_restore.html', **data)
