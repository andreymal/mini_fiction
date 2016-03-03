#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import db_session
from flask import Blueprint, current_app, request, abort, render_template
from flask_login import current_user
from flask_babel import gettext

from mini_fiction.ajax.utils import ajax_login_required
from mini_fiction.models import Story, Comment
from mini_fiction.forms.comment import CommentForm
from mini_fiction.utils.misc import Paginator


bp = Blueprint('ajax_comment', __name__)


@bp.route('/story/<int:story_id>/comment/add/', methods=('GET', 'POST',))
@db_session
@ajax_login_required
def add(story_id):
    user = current_user._get_current_object()
    story = Story.accessible(user).filter(lambda x: x.id == story_id).first()
    if not story:
        abort(404)

    form = CommentForm(request.form)
    if form.validate_on_submit():
        comment = Comment.bl.create(story, form.text.data, user, request.remote_addr)
        return render_template('includes/comments.html', comments=[comment], story=story)
    data = {
        'page_title': gettext('Add new comment'),
        'form': form,
        'story': story,
        'edit': False,
    }
    return render_template('includes/ajax/comment_ajax_edit_window.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:pk>/edit/', methods=('GET', 'POST',))
@db_session
@ajax_login_required
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
        return render_template('includes/comments.html', comments=[comment], story=comment.story)
    data = {
        'page_title': gettext('Edit comment'),
        'form': form,
        'story': comment.story,
        'comment': comment,
        'edit': True,
    }
    return render_template('includes/ajax/comment_ajax_edit_window.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:pk>/delete/', methods=('GET', 'POST',))
@db_session
@ajax_login_required
def delete(story_id, pk):
    user = current_user._get_current_object()
    comment = Comment.get(id=pk)
    if not comment or comment.story.id != story_id:
        abort(404)
    if not comment.editable_by(user):
        abort(403)

    if request.method == 'POST':
        comment_id = comment.id
        comment.bl.delete()
        return str(comment_id)
    data = {
        'page_title': gettext('Confirm delete comment'),
        'story': comment.story,
        'comment': comment,
    }
    return render_template('includes/ajax/comment_ajax_confirm_delete.html', **data)


@bp.route('/story/<int:story_id>/comments/page/<int:page>/')
@db_session
def comments_story(story_id, page):
    """ Подгрузка комментариев к рассказу """

    story = Story.get(id=story_id)
    if not story or not current_user.is_staff and not story.published and not story.editable_by(current_user):
        abort(404)

    comments_list = story.comments.select().order_by(Comment.id)
    comments_count = comments_list.count()
    paged = Paginator(
        number=page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['page'],
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and page != 1:
        abort(404)
    return render_template('includes/comments.html', comments=comments, story=story)


@bp.route('/accounts/profile/comments/page/<int:page>/', defaults={'user_id': None})
@bp.route('/accounts/<int:user_id>/comments/page/<int:page>/')
@db_session
def comments_author(user_id, page):
    """ Подгрузка комментариев для профиля """
    if user_id is None:
        if not current_user.is_authenticated:
            abort(403)
        user_id = current_user.id

    comments_list = Comment.select(lambda x: x.author.id == user_id and x.story.approved and not x.story.draft).order_by(Comment.id.desc())
    comments_count = comments_list.count()
    paged = Paginator(
        number=page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['author_page'],
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and page != 1:
        abort(404)
    return render_template('includes/comments.html', comments=comments)
