#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from flask import Blueprint, Response, current_app, request, render_template, abort, redirect, url_for, send_file, jsonify, g
from flask_babel import gettext
from flask_login import current_user, login_required
from pony.orm import db_session

from mini_fiction.forms.story import StoryForm
from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Story, Chapter, Rating, StoryLog, Favorites, Bookmark
from mini_fiction.validation import ValidationError
from mini_fiction.utils.misc import calc_maxdepth

bp = Blueprint('story', __name__)


def get_story(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.has_access(current_user._get_current_object()):
        abort(403)
    return story


@bp.route('/<int:pk>/', defaults={'comments_page': -1})
@bp.route('/<int:pk>/comments/page/<int:comments_page>/')
@db_session
def view(pk, comments_page):
    user = current_user._get_current_object()
    story = get_story(pk)

    per_page = current_app.config['COMMENTS_COUNT']['page']
    maxdepth = None if request.args.get('fulltree') == '1' else calc_maxdepth(current_user)

    comments_count, paged, comments_tree_list = story.bl.paginate_comments(comments_page, per_page, maxdepth)
    if not comments_tree_list and paged.number != 1:
        abort(404)
    last_viewed_comment = story.bl.last_viewed_comment_by(user)

    chapters = story.chapters.select().order_by(Chapter.order, Chapter.id)[:]

    if user.is_authenticated:
        story.bl.viewed(user)
        if len(chapters) == 1:
            chapters[0].bl.viewed(user)
        user_vote = story.votes.select(lambda x: x.author == user).first()
    else:
        user_vote = None

    comment_ids = [x[0].id for x in comments_tree_list]
    if user.is_authenticated:
        comment_votes_cache = story.bl.select_comment_votes(user, comment_ids)
    else:
        comment_votes_cache = {i: 0 for i in comment_ids}

    data = {
        'story': story,
        'vote': user_vote,
        'comments_tree_list': comments_tree_list,
        'comments_count': comments_count,
        'comment_votes_cache': comment_votes_cache,
        'last_viewed_comment': last_viewed_comment,
        'chapters': chapters,
        'num_pages': paged.num_pages,
        'page_current': comments_page,
        'page_title': story.title,
        'comment_form': CommentForm(),
        'page_obj': paged,
    }
    return render_template('story_view.html', **data)


# this is for ajax links


@bp.route('/<int:pk>/approve/', methods=('POST',))
@db_session
@login_required
def approve(pk):
    user = current_user._get_current_object()
    if not user.is_staff:
        abort(403)  # TODO: refactor exceptions and move to bl
    story = Story.get(id=pk)
    if not story:
        abort(404)
    story.bl.approve(user, not story.approved)
    if g.is_ajax:
        return jsonify({'success': True, 'story_id': story.id, 'approved': story.approved})
    else:
        return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/publish/', methods=('POST',))
@db_session
@login_required
def publish(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)

    user = current_user._get_current_object()
    if not user.is_staff and not story.bl.editable_by(user):
        abort(403)

    if story.bl.publish(user, story.draft):  # draft == not published
        if g.is_ajax:
            return jsonify({'success': True, 'story_id': story.id, 'published': not story.draft})
        else:
            return redirect(url_for('story.view', pk=story.id))
    else:
        data = {
            'page_title': 'Неудачная попытка публикации',
            'story': story,
            'need_words': current_app.config['PUBLISH_SIZE_LIMIT']
        }
        html = render_template('includes/ajax/story_ajax_publish_warning.html', **data)
        if g.is_ajax:
            return jsonify({'success': False, 'page_content': {'modal': html}})
        else:
            return redirect(url_for('story.view', pk=story.id))  # TODO: add warning here too


@bp.route('/<int:pk>/favorite/', methods=('POST',))
@db_session
@login_required
def favorite(pk):
    story = get_story(pk)
    user = current_user._get_current_object()
    f = story.favorites.select(lambda x: x.author == user).first()
    if f:
        f.delete()
        f = None
    else:
        f = Favorites(author=user, story=story)
    if g.is_ajax:
        return jsonify({'success': True, 'story_id': story.id, 'favorited': f is not None})
    else:
        return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/bookmark/', methods=('POST',))
@db_session
@login_required
def bookmark(pk):
    story = get_story(pk)
    user = current_user._get_current_object()
    b = story.bookmarks.select(lambda x: x.author == user).first()
    if b:
        b.delete()
        b = None
    else:
        b = Bookmark(author=user, story=story)
    if g.is_ajax:
        return jsonify({'success': True, 'story_id': story.id, 'bookmarked': b is not None})
    else:
        return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/vote/<int:value>/', methods=('POST',))
@db_session
@login_required
def vote(pk, value):
    story = get_story(pk)
    user = current_user._get_current_object()

    try:
        story.bl.vote(user, value, ip=request.remote_addr)
    except ValueError as exc:  # TODO: refactor exceptions
        if g.is_ajax:
            return jsonify({'error': str(exc), 'success': False, 'story_id': story.id}), 403
        else:
            abort(403)

    if g.is_ajax:
        html = render_template('includes/story_header_info.html', story=story)
        return jsonify({'success': True, 'story_id': story.id, 'value': value, 'html': html})
    else:
        return redirect(url_for('story.view', pk=story.id))


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
        edit_log=story.edit_log.select().order_by(StoryLog.created_at.desc()).prefetch(StoryLog.user),
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
    if not story.bl.editable_by(user):
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
    if not story.bl.deletable_by(user):
        abort(403)

    if request.method == 'POST':
        story.bl.delete()
        return redirect(url_for('index.index'))

    page_title = 'Подтверждение удаления рассказа'
    data = {
        'page_title': page_title,
        'story': story,
    }

    if g.is_ajax:
        html = render_template('includes/ajax/story_ajax_confirm_delete.html', page_title=page_title, story=story)
        return jsonify({'page_content': {'modal': html, 'title': page_title}})
    else:
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
