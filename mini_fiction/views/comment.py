#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, render_template, abort, redirect, url_for
from flask_babel import gettext
from flask_login import current_user, login_required
from pony.orm import db_session

from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Story, Comment

bp = Blueprint('comment', __name__)


@bp.route('/story/<int:story_id>/comment/add/', methods=('GET', 'POST'))
@db_session
@login_required
def add(story_id):
    user = current_user._get_current_object()
    story = Story.accessible(user).filter(lambda x: x.id == story_id).first()
    if not story:
        abort(404)

    form = CommentForm(request.form)
    if form.validate_on_submit():
        comment = Comment.bl.create(story, form.text.data, user, request.remote_addr)
        return redirect(url_for('story.view', pk=story.id))
    data = {
        'page_title': gettext('Add new comment'),
        'form': form,
        'story': story,
        'edit': False,
    }
    return render_template('comment_work.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:pk>/edit/', methods=('GET', 'POST'))
@db_session
@login_required
def edit(story_id, pk):
    user = current_user._get_current_object()
    comment = Comment.get(id=pk)
    if not comment or comment.story.id != story_id:
        abort(404)
    if not comment.editable_by(user):
        abort(403)

    form = CommentForm(request.form, data={'text': comment.text})
    if form.validate_on_submit():
        comment.bl.update(form.text.data)
        return redirect(url_for('story.view', pk=comment.story.id))
    data = {
        'page_title': gettext('Edit comment'),
        'form': form,
        'story': comment.story,
        'comment': comment,
        'edit': True,
    }
    return render_template('comment_work.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@login_required
def delete(story_id, pk):
    user = current_user._get_current_object()
    comment = Comment.get(id=pk)
    if not comment or comment.story.id != story_id:
        abort(404)
    if not comment.editable_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.delete()
        return redirect(url_for('story.view', pk=story_id))
    data = {
        'page_title': gettext('Confirm delete comment'),
        'story': comment.story,
        'comment': comment,
    }
    return render_template('comment_confirm_delete.html', **data)
