#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template
from flask_babel import gettext
from pony.orm import select, db_session

from mini_fiction.models import Story, Category, Chapter, StoryComment
from mini_fiction.utils.views import cached_lists

bp = Blueprint('index', __name__)


@bp.route('/')
@db_session
def index():
    page_title = gettext('Index')

    categories = Category.select()[:]

    stories = Story.select_published().order_by(Story.date.desc(), Story.id.desc())
    stories = stories.prefetch(Story.characters, Story.categories, Story.coauthors)
    stories = stories[:current_app.config['STORIES_COUNT']['main']]

    chapters = select(c for c in Chapter if c.story.approved and not c.story.draft and c.order != 1)
    # MySQL query optimization
    # TODO: cacheops alternative?
    # FIXME: good for comments, but not correct for chapters
    opt_chapter_id = current_app.cache.get('index_opt_chapter_id')
    if opt_chapter_id is not None:
        chapters = chapters.filter(lambda x: x.id >= opt_chapter_id)
    chapters = chapters.order_by(Chapter.date.desc(), Chapter.id.desc())
    chapters = chapters[:current_app.config['CHAPTERS_COUNT']['main']]
    if len(chapters) == current_app.config['CHAPTERS_COUNT']['main']:
        current_app.cache.set('index_opt_chapter_id', chapters[-1].id - 500, timeout=1200)

    story_ids = [y.story.id for y in chapters]
    chapters_stories = select(x for x in Story if x.id in story_ids).prefetch(Story.coauthors)[:]
    chapters_stories = {x.id: x for x in chapters_stories}
    chapters = [(x, chapters_stories[x.story.id]) for x in chapters]

    comments = StoryComment.select(lambda x: x.story_published and not x.deleted).order_by(StoryComment.id.desc())
    comments = comments[:current_app.config['COMMENTS_COUNT']['main']]

    data = {
        'categories': categories,
        'stories': stories,
        'chapters': chapters,
        'comments': comments,
        'comments_short': True,
        'page_title': page_title,
    }
    data.update(cached_lists([x.id for x in stories]))

    return render_template('index.html', **data)
