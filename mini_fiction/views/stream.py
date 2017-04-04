#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from pony.orm import db_session
from flask import Blueprint, current_app
from flask_login import current_user

from mini_fiction.models import Story, Chapter, StoryContributor, StoryComment
from mini_fiction.utils.views import paginate_view, cached_lists


bp = Blueprint('stream', __name__)


@bp.route('/stories/page/last/', defaults={'page': -1})
@bp.route('/stories/', defaults={'page': 1})
@bp.route('/stories/page/<int:page>/')
@db_session
def stories(page):
    objects = Story.select_published().order_by(Story.first_published_at.desc(), Story.id.desc())
    objects = objects.prefetch(Story.characters, Story.categories, Story.contributors, StoryContributor.user)
    return paginate_view(
        'stream/stories.html',
        objects,
        count=objects.count(),
        page_title='Лента добавлений',
        objlistname='stories',
        per_page=current_app.config['STORIES_COUNT']['stream'],
        extra_context=lambda stories_list, _: cached_lists([x.id for x in stories_list])
    )


@bp.route('/chapters/page/last/', defaults={'page': -1})
@bp.route('/chapters/', defaults={'page': 1})
@bp.route('/chapters/page/<int:page>/')
@db_session
def chapters(page):
    objects = orm.select(c for c in Chapter if not c.draft and c.story_published and c.order != 1)
    objects = objects.prefetch(Chapter.text, Chapter.story, Story.contributors, StoryContributor.user)
    objects = objects.order_by(Chapter.first_published_at.desc(), Chapter.order.desc())

    return paginate_view(
        'stream/chapters.html',
        objects,
        count=objects.count(),
        page_title='Лента обновлений',
        objlistname='chapters',
        per_page=current_app.config['CHAPTERS_COUNT']['stream'],
    )


@bp.route('/comments/page/last/', defaults={'page': -1})
@bp.route('/comments/', defaults={'page': 1})
@bp.route('/comments/page/<int:page>/')
@db_session
def comments(page):
    objects = StoryComment.select(lambda x: x.story_published and not x.deleted).order_by(StoryComment.id.desc())

    return paginate_view(
        'stream/comments.html',
        objects,
        count=objects.count(),
        page_title='Лента комментариев',
        objlistname='comments',
        per_page=current_app.config['COMMENTS_COUNT']['stream'],
        extra_context=lambda comments_list, _: {
            'with_story_link': True,
            'comment_votes_cache': Story.bl.select_comment_votes(
                current_user._get_current_object(),
                [x.id for x in comments_list]
            ) if current_user.is_authenticated else {}
        }
    )
