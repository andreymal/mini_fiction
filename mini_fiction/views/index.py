#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template
from flask_babel import gettext
from pony.orm import select, db_session

from mini_fiction.models import Story, StoryContributor, Category, Chapter, StoryComment, NewsItem
from mini_fiction.utils.views import cached_lists

bp = Blueprint('index', __name__)


@bp.route('/')
@db_session
def index():
    page_title = gettext('Index')

    categories = Category.select()[:]

    pinned_stories = list(
        Story.select_published().filter(lambda x: x.pinned).order_by(Story.first_published_at.desc())
    )

    stories = Story.select_published().filter(lambda x: not x.pinned).order_by(Story.first_published_at.desc())
    stories = stories.prefetch(Story.characters, Story.categories, Story.contributors, StoryContributor.user)
    stories = pinned_stories + stories[:max(1, current_app.config['STORIES_COUNT']['main'] - len(pinned_stories))]

    chapters = select(c for c in Chapter if not c.draft and c.story_published and c.order != 1)
    chapters = chapters.order_by(Chapter.first_published_at.desc(), Chapter.order.desc())
    chapters = chapters[:current_app.config['CHAPTERS_COUNT']['main']]

    story_ids = [y.story.id for y in chapters]
    chapters_stories = select(x for x in Story if x.id in story_ids).prefetch(Story.contributors, StoryContributor.user)[:]
    chapters_stories = {x.id: x for x in chapters_stories}
    chapters = [(x, chapters_stories[x.story.id]) for x in chapters]

    comments = StoryComment.select(lambda x: x.story_published and not x.deleted).order_by(StoryComment.id.desc())
    comments = comments[:current_app.config['COMMENTS_COUNT']['main']]

    news = NewsItem.select().order_by(NewsItem.id.desc())[:3]

    data = {
        'categories': categories,
        'stories': stories,
        'chapters': chapters,
        'comments': comments,
        'comments_short': True,
        'news': news,
        'page_title': page_title,
    }
    data.update(cached_lists([x.id for x in stories]))

    return render_template('index.html', **data)
