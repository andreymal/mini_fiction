#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pytz
from flask import Blueprint, Response, current_app, url_for, request, abort
from flask_babel import gettext, ngettext
from feedgen.feed import FeedGenerator
from markupsafe import Markup
from pony.orm import select, db_session, desc

from mini_fiction.models import Story, Chapter, Author
from mini_fiction.utils.misc import sitename


bp = Blueprint('feeds', __name__)


def _add_story_entry(feed, story, order='append'):
    entry = feed.add_entry(order=order)
    entry.id(url_for('story.view', pk=story.id, _external=True))
    entry.link(href=url_for('story.view', pk=story.id, _external=True))
    entry.title(story.title)
    entry.content(Markup(story.summary).striptags())
    entry.author([
        {'name': author.username, 'uri': url_for('author.info', user_id=author.id, _external=True)}
        for author in story.bl.get_authors()
    ])
    entry.published(pytz.UTC.fromutc(story.first_published_at or story.date))
    entry.updated(pytz.UTC.fromutc(
        max(story.first_published_at or story.date, story.updated)
    ))

    return entry


def _add_stories_to_feed(feed, stories):
    last_update = datetime(1970, 1, 1, 0)

    for story in stories:
        _add_story_entry(feed, story)
        last_update = max(
            last_update,
            story.first_published_at or story.date,
            story.updated,
        )

    return last_update


@bp.route('/stories/', endpoint='stories')
@db_session
def feed_stories():
    feed = FeedGenerator()
    feed.title('Новые рассказы — {}'.format(sitename()))
    feed.subtitle('Новые фанфики')
    feed.id(request.url)
    feed.link(href=request.url, rel='self')

    count = current_app.config['RSS'].get('stories', 20)
    stories = Story.select_published().sort_by(desc(Story.first_published_at), desc(Story.id))[:count]
    last_update = _add_stories_to_feed(feed, stories)

    feed.updated(pytz.UTC.fromutc(last_update))
    return Response(feed.atom_str(pretty=True), mimetype='application/atom+xml')


@bp.route('/stories/top/', endpoint='top')
@db_session
def feed_stories_top():
    period = request.args.get('period', 0)
    try:
        period = int(period)
    except ValueError:
        period = 0

    if period == 7:
        title = gettext('Top stories for the week')
    elif period == 30:
        title = gettext('Top stories for the month')
    elif period == 365:
        title = gettext('Top stories for the year')
    elif period == 0:
        title = gettext('Top stories for all time')
    else:
        title = ngettext('Top stories in %(num)d day', 'Top stories in %(num)d days', period)

    feed = FeedGenerator()
    feed.title('{} — {}'.format(title, sitename()))
    feed.subtitle('Топ рассказов')
    feed.id(request.url)
    feed.link(href=request.url, rel='self')

    count = current_app.config['RSS'].get('stories', 20)
    stories = Story.bl.select_top(period)[:count]
    last_update = _add_stories_to_feed(feed, stories)

    feed.updated(pytz.UTC.fromutc(last_update))
    return Response(feed.atom_str(pretty=True), mimetype='application/atom+xml')


@bp.route('/accounts/<int:user_id>/', endpoint='accounts')
@db_session
def feed_accounts(user_id):
    author = Author.get(id=user_id)
    if not author:
        abort(404)

    feed = FeedGenerator()
    feed.title('Новые рассказы автора {} — {}'.format(author.username, sitename()))
    feed.subtitle('Новые фанфики')
    feed.id(request.url)
    feed.link(href=request.url, rel='self')

    count = current_app.config['RSS'].get('accounts', 10)
    stories = Story.bl.select_by_author(author).sort_by(desc(Story.first_published_at), desc(Story.id))[:count]
    last_update = _add_stories_to_feed(feed, stories)

    feed.updated(pytz.UTC.fromutc(last_update))
    return Response(feed.atom_str(pretty=True), mimetype='application/atom+xml')


@bp.route('/chapters/', endpoint='chapters')
@db_session
def feed_chapters():
    feed = FeedGenerator()
    feed.title('Обновления глав — {}'.format(sitename()))
    feed.subtitle('Новые главы рассказов')
    feed.id(request.url)
    feed.link(href=request.url, rel='self')
    last_update = datetime(1970, 1, 1, 0)

    chapters = select(c for c in Chapter if not c.draft and c.story_published)
    chapters = chapters.sort_by(desc(Chapter.first_published_at), desc(Chapter.order))
    count = current_app.config['RSS'].get('chapters', 20)
    chapters = chapters.prefetch(Chapter.story)[:count]

    for chapter in chapters:
        story = chapter.story
        data = chapter.text_preview
        chapter_url = url_for('chapter.view', story_id=story.id, chapter_order=chapter.order, _external=True)

        entry = feed.add_entry(order='append')
        entry.id(chapter_url)
        entry.link(href=chapter_url)
        entry.title('{} : {}'.format(chapter.autotitle, story.title))
        entry.content(data)
        entry.author([
            {'name': author.username, 'uri': url_for('author.info', user_id=author.id, _external=True)}
            for author in story.bl.get_authors()
        ])
        entry.published(pytz.UTC.fromutc(chapter.date))
        entry.updated(pytz.UTC.fromutc(chapter.updated))
        last_update = max(last_update, chapter.updated)

    feed.updated(pytz.UTC.fromutc(last_update))
    return Response(feed.atom_str(pretty=True), mimetype='application/atom+xml')


@bp.route('/story/<int:story_id>/', endpoint='story')
@db_session
def feed_story(story_id):
    story = Story.select_published().filter(lambda x: x.id == story_id).prefetch(Story.chapters).first()
    if not story:
        abort(404)

    feed = FeedGenerator()
    feed.title(story.title)
    feed.id(request.url)
    feed.link(href=request.url, rel='self')
    last_update = datetime(1970, 1, 1, 0)

    chapters = [c for c in story.chapters if not c.draft]
    for c in chapters:
        assert c.first_published_at is not None, 'database is inconsistent: story {} has non-draft and non-published chapter {}'.format(story.id, c.order)
    chapters.sort(key=lambda x: (x.first_published_at, x.order), reverse=True)

    for chapter in chapters:
        data = chapter.text_preview
        chapter_url = url_for('chapter.view', story_id=story.id, chapter_order=chapter.order, _external=True)

        entry = feed.add_entry(order='append')
        entry.id(chapter_url)
        entry.link(href=chapter_url)
        entry.title(chapter.autotitle)
        entry.content(data)
        entry.published(pytz.UTC.fromutc(chapter.date))
        entry.updated(pytz.UTC.fromutc(chapter.updated))
        last_update = max(last_update, chapter.updated)

    feed.updated(pytz.UTC.fromutc(last_update))
    return Response(feed.atom_str(pretty=True), mimetype='application/atom+xml')
