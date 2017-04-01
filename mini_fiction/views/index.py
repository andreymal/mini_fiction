#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template
from flask_babel import gettext
from pony.orm import select, db_session

from mini_fiction.models import Story, CoAuthorsStory, Category, Chapter, StoryComment
from mini_fiction.utils.views import cached_lists

bp = Blueprint('index', __name__)


@bp.route('/')
@db_session
def index():
    page_title = gettext('Index')

    categories = Category.select()[:]

    stories = Story.select_published().order_by(Story.first_published_at.desc(), Story.id.desc())
    stories = stories.prefetch(Story.characters, Story.categories, Story.coauthors)
    stories = stories[:current_app.config['STORIES_COUNT']['main']]

    chapters = select(c for c in Chapter if c.story_published and c.order != 1)
    chapters = chapters.order_by(Chapter.date.desc())
    chapters = chapters[:current_app.config['CHAPTERS_COUNT']['main']]

    story_ids = [y.story.id for y in chapters]
    chapters_stories = select(x for x in Story if x.id in story_ids).prefetch(Story.coauthors, CoAuthorsStory.author)[:]
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
