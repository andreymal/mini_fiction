#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, Markup, current_app, url_for, request, abort
from werkzeug.contrib.atom import AtomFeed
from pony.orm import select, db_session

from mini_fiction.models import Story, Chapter, Author
from mini_fiction.utils.misc import sitename

bp = Blueprint('feeds', __name__)


@bp.route('/stories/', endpoint='stories')
@db_session
def feed_stories():
    feed = AtomFeed(
        title='Новые рассказы — {}'.format(sitename()),
        subtitle='Новые фанфики',
        feed_url=request.url,
        url=request.url_root
    )
    count = current_app.config['RSS'].get('stories', 20)
    stories = Story.select_published().order_by(Story.first_published_at.desc(), Story.id.desc())[:count]
    for story in stories:
        author = story.authors[0]
        feed.add(
            story.title,
            Markup(story.summary).striptags(),
            content_type='text',
            author=author.username,
            url=url_for('story.view', pk=story.id, _external=True),
            updated=story.updated,
            published=story.first_published_at or story.date
        )
    return feed.get_response()


@bp.route('/accounts/<int:user_id>/', endpoint='accounts')
@db_session
def feed_accounts(user_id):
    author = Author.get(id=user_id)
    if not author:
        abort(404)

    feed = AtomFeed(
        title='Новые рассказы автора {} — {}'.format(author.username, sitename()),
        subtitle='Новые фанфики',
        feed_url=request.url,
        url=request.url_root
    )
    count = current_app.config['RSS'].get('accounts', 10)
    stories = Story.bl.select_by_author(author).order_by(Story.first_published_at.desc(), Story.id.desc())[:count]
    for story in stories:
        feed.add(
            story.title,
            Markup(story.summary).striptags(),
            content_type='text',
            author=author.username,
            url=url_for('story.view', pk=story.id, _external=True),
            updated=story.updated,
            published=story.first_published_at or story.date
        )
    return feed.get_response()


@bp.route('/chapters/', endpoint='chapters')
@db_session
def feed_chapters():
    feed = AtomFeed(
        title='Обновления глав — {}'.format(sitename()),
        subtitle='Новые главы рассказов',
        feed_url=request.url,
        url=request.url_root
    )

    chapters = select(c for c in Chapter if not c.draft and c.story_published)
    chapters = chapters.order_by(Chapter.first_published_at.desc(), Chapter.order.desc())
    count = current_app.config['RSS'].get('chapters', 20)
    chapters = chapters.prefetch(Chapter.story)[:count]

    for chapter in chapters:
        story = chapter.story
        author = story.authors[0]
        data = chapter.text_preview
        feed.add(
            chapter.autotitle,
            data,
            content_type='text',
            author=author.username,
            url=url_for('chapter.view', story_id=story.id, chapter_order=chapter.order, _external=True),
            updated=chapter.updated,
            published=chapter.date,
        )
    return feed.get_response()


@bp.route('/story/<int:story_id>/', endpoint='story')
@db_session
def feed_story(story_id):
    story = Story.select_published().filter(lambda x: x.id == story_id).prefetch(Story.chapters).first()
    if not story:
        abort(404)

    feed = AtomFeed(
        title=story.title,
        feed_url=request.url,
        url=request.url_root
    )

    chapters = [c for c in story.chapters if not c.draft]
    for c in chapters:
        assert c.first_published_at is not None, 'database is inconsistent: story {} has non-draft and non-published chapter {}'.format(story.id, c.order)
    chapters.sort(key=lambda x: (x.first_published_at, x.order), reverse=True)

    for chapter in chapters:
        data = chapter.text_preview
        feed.add(
            chapter.autotitle,
            data,
            content_type='text',
            url=url_for('chapter.view', story_id=story.id, chapter_order=chapter.order, _external=True),
            updated=chapter.updated,
            published=chapter.date,
        )
    return feed.get_response()
