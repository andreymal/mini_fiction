#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, Markup, current_app, url_for, request, abort
from werkzeug.contrib.atom import AtomFeed
from pony.orm import select, db_session

from mini_fiction.models import Story, Chapter
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
    stories = Story.select_published().order_by(Story.date.desc(), Story.id.desc())[:current_app.config['RSS']['stories']]
    for story in stories:
        coauthor = story.coauthors.select().first()
        feed.add(
            story.title,
            Markup(story.summary).striptags(),
            content_type='text',
            author=coauthor.author.username if coauthor else 'N/A',
            url=url_for('story.view', pk=story.id, _external=True),
            updated=story.updated,
            published=story.date
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

    chapters = select(c for c in Chapter if c.story_published)
    chapters = chapters.order_by(Chapter.date.desc())
    chapters = chapters.prefetch(Chapter.story)[:current_app.config['RSS']['chapters']]

    for chapter in chapters:
        story = chapter.story
        coauthor = story.coauthors.select().first()
        data = Markup(chapter.text).striptags()[:251]
        if len(data) == 251:
            data = data[:-1] + '…'
        feed.add(
            chapter.title,
            data,
            content_type='text',
            author=coauthor.author.username if coauthor else 'N/A',
            url=url_for('chapter.view', story_id=story.id, chapter_order=chapter.order, _external=True),
            updated=chapter.updated,
            published=chapter.date,
        )
    return feed.get_response()


@bp.route('/story/<int:story_id>/', endpoint='story')
@db_session
def feed_story(story_id):
    story = Story.select(lambda x: x.id == story_id).prefetch(Story.chapters).first()
    if not story:
        abort(404)

    feed = AtomFeed(
        title=story.title,
        feed_url=request.url,
        url=request.url_root
    )

    chapters = sorted(story.chapters, key=lambda x: x.date, reverse=True)
    for chapter in chapters:
        data = Markup(chapter.text).striptags()[:251]
        if len(data) == 251:
            data = data[:-1] + '…'
        feed.add(
            chapter.title,
            data,
            content_type='text',
            url=url_for('chapter.view', story_id=story.id, chapter_order=chapter.order, _external=True),
            updated=chapter.updated,
            published=chapter.date,
        )
    return feed.get_response()
