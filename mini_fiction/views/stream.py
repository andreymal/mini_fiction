#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from pony.orm import db_session
from flask import Blueprint, current_app, render_template, abort, request
from flask_babel import gettext
from flask_login import current_user

from mini_fiction.bl.migration import enrich_stories
from mini_fiction.models import Story, Chapter, StoryContributor, StoryComment, StoryLocalComment, NewsComment, StoryTag, Tag
from mini_fiction.utils.views import cached_lists
from mini_fiction.utils.misc import Paginator, IndexPaginator


bp = Blueprint('stream', __name__)


@bp.route('/stories/page/last/', defaults={'page': -1})
@bp.route('/stories/', defaults={'page': 1})
@bp.route('/stories/page/<int:page>/')
@db_session
def stories(page):
    objects = Story.select_published().filter(lambda x: not x.pinned)
    objects = objects.sort_by(orm.desc(Story.first_published_at), orm.desc(Story.id))
    objects = objects.prefetch(
        Story.characters, Story.contributors, StoryContributor.user,
        Story.tags, StoryTag.tag, Tag.category,
    )

    page_obj = IndexPaginator(
        page,
        total=objects.count(),
        per_page=current_app.config['STORIES_COUNT']['stream'],
    )
    objects = page_obj.slice(objects)

    if page == 1:
        pinned_stories = list(
            Story.select_published().filter(lambda x: x.pinned).sort_by(orm.desc(Story.first_published_at))
        )
        objects = pinned_stories + objects

    if not objects and page != 1:
        abort(404)

    enrich_stories(objects)

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
    objects = objects.sort_by(orm.desc(Chapter.first_published_at), orm.desc(Chapter.order))

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['CHAPTERS_COUNT']['stream'])
    objects = page_obj.slice_or_404(objects)

    return render_template(
        'stream/chapters.html',
        page_title=gettext('Updates feed'),
        chapters=objects,
        page_obj=page_obj,
        robots_noindex=True,
        **cached_lists([x.story.id for x in objects])
    )


@bp.route('/comments/page/last/', defaults={'page': -1})
@bp.route('/comments/', defaults={'page': 1})
@bp.route('/comments/page/<int:page>/')
@db_session
def comments(page):
    objects = StoryComment.select(lambda x: x.story_published)
    filter_deleted = current_user.is_staff and request.args.get('deleted') == '1'
    if filter_deleted:
        objects = objects.filter(lambda x: x.deleted).sort_by(orm.desc(StoryComment.last_deleted_at))
    else:
        objects = objects.filter(lambda x: not x.deleted).sort_by(orm.desc(StoryComment.id))

    view_args = dict(request.view_args)
    if filter_deleted:
        view_args['deleted'] = '1'
    page_obj = Paginator(
        page,
        objects.count(),
        per_page=current_app.config['COMMENTS_COUNT']['stream'],
        view_args=view_args,
    )
    objects = [('story', x) for x in page_obj.slice_or_404(objects)]

    comment_votes_cache = Story.bl.select_comment_votes(
        current_user,
        [x[1].id for x in objects]
    ) if current_user.is_authenticated else {}

    return render_template(
        'stream/comments.html',
        page_title=gettext('Comments feed'),
        tab='story',
        comments=objects,
        filter_deleted=filter_deleted,
        with_target_link=True,
        comment_votes_cache=comment_votes_cache,
        page_obj=page_obj,
        robots_noindex=True,
        **cached_lists([x[1].story.id for x in objects])
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
        objects = objects.filter(lambda x: x.deleted).sort_by(orm.desc(StoryLocalComment.last_deleted_at))
    else:
        objects = objects.filter(lambda x: not x.deleted).sort_by(orm.desc(StoryLocalComment.id))

    view_args = dict(request.view_args)
    if filter_deleted:
        view_args['deleted'] = '1'
    page_obj = Paginator(
        page,
        objects.count(),
        per_page=current_app.config['COMMENTS_COUNT']['stream'],
        view_args=view_args,
    )
    objects = [('local', x) for x in page_obj.slice_or_404(objects)]

    comment_votes_cache = {}  # FIXME: здесь пересечение айдишников с айдшниками комментов к рассказам

    return render_template(
        'stream/comments.html',
        page_title=gettext('Comments feed'),
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
        objects = objects.filter(lambda x: x.deleted).sort_by(orm.desc(NewsComment.last_deleted_at))
    else:
        objects = objects.filter(lambda x: not x.deleted).sort_by(orm.desc(NewsComment.id))

    view_args = dict(request.view_args)
    if filter_deleted:
        view_args['deleted'] = '1'
    page_obj = Paginator(
        page,
        objects.count(),
        per_page=current_app.config['COMMENTS_COUNT']['stream'],
        view_args=view_args,
    )
    objects = [('news', x) for x in page_obj.slice_or_404(objects)]

    comment_votes_cache = {}  # FIXME: здесь пересечение айдишников с айдшниками комментов к рассказам

    return render_template(
        'stream/comments.html',
        page_title=gettext('Comments feed'),
        tab='news',
        comments=objects,
        filter_deleted=filter_deleted,
        with_target_link=True,
        comment_votes_cache=comment_votes_cache,
        page_obj=page_obj,
        robots_noindex=True,
    )
