#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template
from flask_babel import gettext
from pony.orm import select, db_session

from mini_fiction.models import Story, StoryContributor, Category, Chapter, StoryComment, NewsItem, NewsComment
from mini_fiction.utils.views import cached_lists
from mini_fiction.utils.misc import indextitle, sitedescription

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

    news = NewsItem.select().order_by(NewsItem.id.desc())[:3]

    comments_html = current_app.cache.get('index_comments_html')

    if not comments_html:
        story_comments = StoryComment.select(lambda x: x.story_published and not x.deleted).order_by(StoryComment.id.desc())
        story_comments = story_comments[:current_app.config['COMMENTS_COUNT']['main']]

        news_comments = NewsComment.select(lambda x: not x.deleted).order_by(NewsComment.id.desc())
        news_comments = news_comments[:current_app.config['COMMENTS_COUNT']['main']]

        comments = [('story', x) for x in story_comments]
        comments += [('news', x) for x in news_comments]
        comments.sort(key=lambda x: x[1].date, reverse=True)
        comments = comments[:current_app.config['COMMENTS_COUNT']['main']]

        comments_html = render_template(
            'includes/comments_list.html',
            comments=comments,
            comments_short=True,
        )

        current_app.cache.set('index_comments_html', comments_html, 3600)

    data = {
        'categories': categories,
        'stories': stories,
        'chapters': chapters,
        'comments_html': comments_html,
        'news': news,
        'page_title': page_title,
        'full_title': indextitle(),
        'site_description': sitedescription(),
    }
    data.update(cached_lists([x.id for x in stories]))

    return render_template('index.html', **data)
