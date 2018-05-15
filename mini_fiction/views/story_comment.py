#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, url_for, jsonify
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import Story, StoryComment, Author
from mini_fiction.utils.misc import Paginator
from mini_fiction.views import common_comment

bp = Blueprint('story_comment', __name__)


@bp.route('/story/<int:story_id>/comment/add/', methods=('GET', 'POST'))
@db_session
def add(story_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)

    # Все проверки доступа там
    return common_comment.add(
        'story',
        story,
        template='story_comment_work.html',
    )


@bp.route('/story/<int:story_id>/comment/<int:local_id>/')
@db_session
def show(story_id, local_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)

    if not story.bl.has_comments_access(current_user._get_current_object()):
        abort(403)

    comment = StoryComment.get(story=story_id, local_id=local_id)
    if not comment or (comment.deleted and not current_user.is_staff):
        abort(404)

    return common_comment.show('story', comment)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(story_id, local_id):
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.edit(
        'story',
        comment,
        template='story_comment_work.html',
    )


@bp.route('/story/<int:story_id>/comment/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(story_id, local_id):
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.delete(
        'story',
        comment,
        template='story_comment_delete.html',
        template_ajax='includes/ajax/story_comment_delete.html',
        template_ajax_modal=True,
    )


@bp.route('/story/<int:story_id>/comment/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(story_id, local_id):
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=True)
    if not comment:
        abort(404)

    return common_comment.restore(
        'story',
        comment,
        template='story_comment_restore.html',
        template_ajax='includes/ajax/story_comment_restore.html',
        template_ajax_modal=True,
    )


@bp.route('/story/<int:story_id>/comment/<int:local_id>/vote/', methods=('POST',))
@db_session
def vote(story_id, local_id):
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.vote('story', comment)


@bp.route('/ajax/story/<int:story_id>/comments/page/<int:page>/')
@db_session
def ajax(story_id, page):
    story = Story.get(id=story_id)
    if not story:
        abort(404)

    per_page = current_user.comments_per_page or current_app.config['COMMENTS_COUNT']['page']
    link = url_for('story.view', pk=story.id, comments_page=page)

    if request.args.get('last_comment') and request.args['last_comment'].isdigit():
        last_viewed_comment = int(request.args['last_comment'])
    else:
        last_viewed_comment = story.bl.last_viewed_comment_by(current_user)

    return common_comment.ajax(
        'story',
        story,
        link,
        page,
        per_page,
        template_pagination='includes/comments_pagination_story.html',
        last_viewed_comment=last_viewed_comment,
        extra_data={'author_ids': [x.id for x in story.authors]},
    )


@bp.route('/ajax/story/<int:story_id>/comments/tree/<int:local_id>/')
@db_session
def ajax_tree(story_id, local_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)

    comment = story.comments.select(lambda x: x.local_id == local_id).first()
    if not comment:
        abort(404)

    if request.args.get('last_comment') and request.args['last_comment'].isdigit():
        last_viewed_comment = int(request.args['last_comment'])
    else:
        last_viewed_comment = story.bl.last_viewed_comment_by(current_user)

    return common_comment.ajax_tree(
        'story',
        comment,
        target=story,
        last_viewed_comment=last_viewed_comment,
        extra_data={'author_ids': [x.id for x in story.authors]},
    )


# story-specific views


@bp.route('/ajax/accounts/profile/comments/page/<int:page>/')
@db_session
def ajax_author_dashboard(page):
    if not current_user.is_authenticated:
        abort(403)

    comments_list = StoryComment.bl.select_by_story_author(current_user)
    comments_list = comments_list.order_by(StoryComment.id.desc())
    comments_count = comments_list.count()

    paged = Paginator(
        number=page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['author_page'],
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and page != 1:
        abort(404)

    data = {
        'comments': comments,
        'page_obj': paged,
        'comments_short': True,
    }

    return jsonify({
        'success': True,
        'link': url_for('author.info', comments_page=page),
        'comments_count': comments_count,
        'comments_list': render_template('includes/story_comments_list.html', **data),
        'pagination': render_template('includes/comments_pagination_author_dashboard.html', **data),
    })


@bp.route('/ajax/accounts/<int:user_id>/comments/page/<int:page>/')
@db_session
def ajax_author_overview(user_id, page):
    author = Author.get(id=user_id)
    if not author:
        abort(404)

    comments_list = StoryComment.select(lambda x: x.author == author and not x.deleted and x.story_published)
    comments_list = comments_list.order_by(StoryComment.id.desc())
    comments_count = comments_list.count()

    paged = Paginator(
        number=page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['author_page'],
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and page != 1:
        abort(404)

    data = {
        'author': author,
        'comments': comments,
        'page_obj': paged,
        'comments_short': True,
    }

    return jsonify({
        'success': True,
        'link': url_for('author.info', user_id=author.id, comments_page=page),
        'comments_count': comments_count,
        'comments_list': render_template('includes/story_comments_list.html', **data),
        'pagination': render_template('includes/comments_pagination_author_overview.html', **data),
    })
