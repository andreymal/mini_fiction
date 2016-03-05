#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from flask import Blueprint, Response, current_app, request, render_template, abort, redirect, url_for, send_file
from flask_babel import gettext
from flask_login import current_user, login_required
from pony.orm import db_session

from mini_fiction.forms.story import StoryForm
from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Story, Chapter, Rating, StoryEditLogItem, Comment
from mini_fiction.utils.misc import Paginator
from mini_fiction.validation import ValidationError

bp = Blueprint('story', __name__)


def get_story(pk):
    story = Story.accessible(current_user).filter(lambda x: x.id == pk).first()
    if not story:
        story = Story.get(id=pk)
        if not story:
            abort(404)
        if not story.editable_by(current_user):
            abort(403)
    return story


@bp.route('/<int:pk>/', defaults={'comments_page': -1})
@bp.route('/<int:pk>/comments/page/<int:comments_page>/')
@db_session
def view(pk, comments_page):
    story = get_story(pk)
    chapters = story.chapters.select().order_by(Chapter.order, Chapter.id)[:]
    comments_list = story.comments.select().order_by(Comment.id)
    comments_count = comments_list.count()
    paged = Paginator(
        number=comments_page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['page'],
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and paged.number != 1:
        abort(404)
    num_pages = paged.num_pages
    page_title = story.title
    comment_form = CommentForm()

    user = current_user._get_current_object()
    if user.is_authenticated:
        story.bl.viewed(user)
        if len(chapters) == 1:
            chapters[0].bl.viewed(user)
        user_vote = story.votes.select(lambda x: x.author == user).first()
    else:
        user_vote = None

    data = {
       'story': story,
       'vote': user_vote,
       'comments': comments,
       'comments_count': comments_count,
       'chapters': chapters,
       'num_pages': num_pages,
       'page_current': comments_page,
       'page_title': page_title,
       'comment_form': comment_form,
       'page_obj': paged,
    }
    return render_template('story_view.html', **data)


# this is for ajax links


@bp.route('/<int:pk>/approve/', methods=('POST',))
def approve():
    abort(403)


@bp.route('/<int:pk>/publish/', methods=('POST',))
def publish():
    abort(403)


@bp.route('/<int:pk>/favorite/', methods=('POST',))
def favorite():
    abort(403)


@bp.route('/<int:pk>/bookmark/', methods=('POST',))
def bookmark():
    abort(403)


@bp.route('/<int:pk>/vote/<int:value>/', methods=('POST',))
def vote(pk, value):
    abort(403)


@bp.route('/<int:pk>/editlog/')
@db_session
def edit_log(pk):
    user = current_user._get_current_object()
    if not user.is_staff:
        abort(403)

    story = Story.get(id=pk)
    if not story:
        abort(404)
    data = dict(
        edit_log=story.edit_log.select().order_by(StoryEditLogItem.date.desc()).prefetch(StoryEditLogItem.user),
        page_title="История редактирования рассказа \"{}\"".format(story.title),
        story=story,
    )
    return render_template('story_edit_log.html', **data)


@bp.route('/add/', methods=('GET', 'POST'))
@db_session
@login_required
def add():
    user = current_user._get_current_object()
    rating = Rating.select().order_by(Rating.id.desc()).first().id
    form = StoryForm(request.form, data={'finished': 0, 'freezed': 0, 'original': 1, 'rating': rating})
    if form.validate_on_submit():
        try:
            story = Story.bl.create([(user, True)], form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('story.edit', pk=story.id))
    data = {
        'page_title': gettext('New story'),
        'form': form,
        'story_add': True
    }
    return render_template('story_work.html', **data)


@bp.route('/<int:pk>/edit/', methods=('GET', 'POST'))
@db_session
@login_required
def edit(pk):
    user = current_user._get_current_object()
    story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.editable_by(user):
        abort(403)

    data = {
        'story_edit': True,
        'chapters': story.chapters.select().order_by(Chapter.order, Chapter.id)[:],
        'saved': False,
        'story': story
    }

    story_data = {
        'categories': [x.id for x in story.categories],  # TODO: optimize
        'characters': [x.id for x in story.characters],
        'classifications': [x.id for x in story.classifications],
        'rating': story.rating.id,
    }
    for key in ('title', 'summary', 'notes', 'original', 'finished', 'freezed'):
        story_data[key] = getattr(story, key)

    form = StoryForm(request.form, data=story_data)
    if form.validate_on_submit():
        try:
            story = story.bl.update(user, form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            data['saved'] = True

    data['form'] = form
    data['page_title'] = 'Редактирование «{}»'.format(story.title)
    return render_template('story_work.html', **data)


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@login_required
def delete(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    user = current_user._get_current_object()
    if not story.deletable_by(user):
        abort(403)

    if request.method == 'POST':
        story.bl.delete()
        return redirect(url_for('index.index'))

    data = {
        'page_title': 'Подтверждение удаления рассказа',
        'story': story,
    }

    return render_template('story_confirm_delete.html', **data)


@bp.route('/<int:story_id>/download/<filename>', methods=('GET',))
@db_session
def download(story_id, filename):
    if '.' not in filename:
        abort(404)
    filename, extension = filename.split('.', 1)

    from ..downloads import get_format

    debug = current_app.config['DEBUG'] and request.args.get('debug')

    story = get_story(pk=story_id)
    fmt = get_format(extension)
    if fmt is None:
        abort(404)

    url = fmt.url(story)
    if url != request.path:
        return redirect(url)
    filepath = 'stories/%s/%s.%s' % (story_id, filename, extension)

    storage_path = os.path.abspath(os.path.join(current_app.config['MEDIA_ROOT'], filepath))

    if (
        not os.path.exists(storage_path) or
        datetime.fromtimestamp(os.stat(storage_path).st_mtime) < story.updated or
        debug
    ):

        data = fmt.render(
            story=story,
            filename=filename,
            extension=extension,
            debug=debug,
        )

        if not debug:
            if os.path.exists(storage_path):
                os.remove(storage_path)
            elif not os.path.isdir(os.path.dirname(storage_path)):
                os.makedirs(os.path.dirname(storage_path))
            with open(storage_path, 'wb') as fp:
                fp.write(data)

    # TODO: delete file if story was deleted
    if not debug:
        # FIXME: fix security before sending static file with nginx
        # TODO: for example, /media/stories/{md5(updated + secret_random_story_key)}/filename.zip
        # return redirect(path to media)
        return send_file(storage_path)
    else:
        response = Response(data, mimetype=fmt.debug_content_type)
        return response
