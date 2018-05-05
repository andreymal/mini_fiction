#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from pony.orm import db_session
from flask import Blueprint, current_app, render_template, abort, request
from flask_login import current_user

from mini_fiction.models import Story, Chapter, StoryContributor, StoryComment, StoryLocalComment, NewsComment
from mini_fiction.utils.views import cached_lists
from mini_fiction.utils.misc import Paginator


bp = Blueprint('stream', __name__)


@bp.route('/stories/page/last/', defaults={'page': -1})
@bp.route('/stories/', defaults={'page': 1})
@bp.route('/stories/page/<int:page>/')
@db_session
def stories(page):
    objects = Story.select_published().order_by(Story.first_published_at.desc(), Story.id.desc())
    objects = objects.prefetch(Story.characters, Story.categories, Story.contributors, StoryContributor.user)

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['STORIES_COUNT']['stream'])
    objects = page_obj.slice_or_404(objects)

    return render_template(
        'stream/stories.html',
        page_title='Лента добавлений',
        stories=objects,
        page_obj=page_obj,
        robots_noindex=True,
        **cached_lists([x.id for x in objects])
    )


@bp.route('/chapters/page/last/', defaults={'page': -1})
@bp.route('/chapters/', defaults={'page': 1})
@bp.route('/chapters/page/<int:page>/')
@db_session
def chapters(page):
    objects = orm.select(c for c in Chapter if not c.draft and c.story_published and c.order != 1)
    objects = objects.prefetch(Chapter.text, Chapter.story, Story.contributors, StoryContributor.user)
    objects = objects.order_by(Chapter.first_published_at.desc(), Chapter.order.desc())

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['CHAPTERS_COUNT']['stream'])
    objects = page_obj.slice_or_404(objects)

    return render_template(
        'stream/chapters.html',
        page_title='Лента обновлений',
        chapters=objects,
        page_obj=page_obj,
        robots_noindex=True,
    )


@bp.route('/comments/page/last/', defaults={'page': -1})
@bp.route('/comments/', defaults={'page': 1})
@bp.route('/comments/page/<int:page>/')
@db_session
def comments(page):
    objects = StoryComment.select(lambda x: x.story_published)
    filter_deleted = current_user.is_staff and request.args.get('deleted') == '1'
    if filter_deleted:
        objects = objects.filter(lambda x: x.deleted).order_by(StoryComment.last_deleted_at.desc())
    else:
        objects = objects.filter(lambda x: not x.deleted).order_by(StoryComment.id.desc())

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['COMMENTS_COUNT']['stream'])
    objects = [('story', x) for x in page_obj.slice_or_404(objects)]

    comment_votes_cache = Story.bl.select_comment_votes(
        current_user._get_current_object(),
        [x[1].id for x in objects]
    ) if current_user.is_authenticated else {}

    return render_template(
        'stream/comments.html',
        page_title='Лента комментариев',
        tab='story',
        comments=objects,
        filter_deleted=filter_deleted,
        with_target_link=True,
        comment_votes_cache=comment_votes_cache,
        page_obj=page_obj,
        robots_noindex=True,
    )


@bp.route('/localcomments/page/last/', defaults={'page': -1})
@bp.route('/localcomments/', defaults={'page': 1})
@bp.route('/localcomments/page/<int:page>/')
@db_session
def storylocalcomments(page):
    if not current_user.is_staff:
        abort(403)

    objects = StoryLocalComment.select()
    filter_deleted = current_user.is_staff and request.args.get('deleted') == '1'
    if filter_deleted:
        objects = objects.filter(lambda x: x.deleted).order_by(StoryLocalComment.last_deleted_at.desc())
    else:
        objects = objects.filter(lambda x: not x.deleted).order_by(StoryLocalComment.id.desc())

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['COMMENTS_COUNT']['stream'])
    objects = [('local', x) for x in page_obj.slice_or_404(objects)]

    comment_votes_cache = {}  # FIXME: здесь пересечение айдишников с айдшниками комментов к рассказам

    return render_template(
        'stream/comments.html',
        page_title='Лента комментариев',
        tab='local',
        comments=objects,
        filter_deleted=filter_deleted,
        with_target_link=True,
        comment_votes_cache=comment_votes_cache,
        page_obj=page_obj,
        robots_noindex=True,
    )


@bp.route('/newscomments/page/last/', defaults={'page': -1})
@bp.route('/newscomments/', defaults={'page': 1})
@bp.route('/newscomments/page/<int:page>/')
@db_session
def newscomments(page):
    objects = NewsComment.select()
    filter_deleted = current_user.is_staff and request.args.get('deleted') == '1'
    if filter_deleted:
        objects = objects.filter(lambda x: x.deleted).order_by(NewsComment.last_deleted_at.desc())
    else:
        objects = objects.filter(lambda x: not x.deleted).order_by(NewsComment.id.desc())

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['COMMENTS_COUNT']['stream'])
    objects = [('news', x) for x in page_obj.slice_or_404(objects)]

    comment_votes_cache = {}  # FIXME: здесь пересечение айдишников с айдшниками комментов к рассказам

    return render_template(
        'stream/comments.html',
        page_title='Лента комментариев',
        tab='news',
        comments=objects,
        filter_deleted=filter_deleted,
        with_target_link=True,
        comment_votes_cache=comment_votes_cache,
        page_obj=page_obj,
        robots_noindex=True,
    )
