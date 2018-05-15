#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from functools import wraps

from flask import Blueprint, current_app, abort, render_template, make_response, url_for
from pony.orm import select, db_session

from mini_fiction.models import Story, Chapter
from mini_fiction.utils.misc import sitename

bp = Blueprint('sitemap', __name__)


def cached_xml_response(cache_key, timeout):
    def decorator(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            k = cache_key.format(*args, **kwargs)

            xml = current_app.cache.get(k)
            if xml is None:
                xml = func(*args, **kwargs).encode('utf-8')
                if len(xml) >= 10 * 1000 * 1000:
                    current_app.logger.warning(
                        'XML Sitemap {!r} size is {:.1f}MB and greater than 10MB'.format(
                            k, len(xml) / 100.0 / 100.0
                        )
                    )
                current_app.cache.set(k, xml, timeout=timeout)

            response = make_response(xml)
            response.headers["Content-Type"] = 'application/xml; charset=utf-8'
            return response

        return wrapped_func

    return decorator


@bp.route('/sitemap.xml')
@cached_xml_response('sitemap_index', timeout=600)
@db_session
def index():
    max_story_id = select(
        x.id for x in Story if not x.draft and x.approved and not x.robots_noindex
    ).order_by('-x.id').first() or 0

    sitemaps = [
        {'url': url_for('sitemap.general', _external=True)},
    ]
    for i in range(0, max_story_id + 1, current_app.config['SITEMAP_STORIES_PER_FILE']):
        sitemaps.append({'url': url_for('sitemap.stories', offset=i, _external=True)})

    return render_template('sitemap/index.xml', sitemaps=sitemaps)


@bp.route('/sitemap/general.xml')
@cached_xml_response('sitemap_general', timeout=30)
@db_session
def general():
    items = [{
        'url': url_for('index.index', _external=True),
        'lastmod': datetime.utcnow(),
        'changefreq': 'hourly',
        'priority': 1.0,
    }]

    return render_template('sitemap/urlset.xml', items=items)


@bp.route('/sitemap/stories_<int:offset>.xml')
@cached_xml_response('sitemap_stories_{offset}', timeout=30)
@db_session
def stories(offset):
    per_file = current_app.config['SITEMAP_STORIES_PER_FILE']

    # Валидация значения offset
    if offset < 0:
        abort(404)
    if offset % per_file != 0:
        abort(404)

    max_story_id = select(
        x.id for x in Story if not x.draft and x.approved and not x.robots_noindex
    ).order_by('-x.id').first() or 0
    if offset > max_story_id:
        abort(404)

    min_id = offset
    max_id = offset + per_file

    now = datetime.utcnow()

    # Сюда складируем все ссылки
    items = []

    # Собираем ссылки на рассказы
    stories = select(
        (x.id, x.first_published_at, x.updated) for x in Story
        if x.id >= min_id and x.id < max_id and not x.draft and x.approved and not x.robots_noindex
    )[:]
    story_ids = [x[0] for x in stories]
    stories.sort(key=lambda x: x[1], reverse=True)

    for story_id, first_published_at, updated_at in stories:
        if updated_at < first_published_at:
            updated_at = first_published_at
        delta = now - first_published_at
        if delta.days < 7:
            changefreq = 'hourly'
            priority = 1.0
        elif delta.days < 60:
            changefreq = 'daily'
            priority = 0.5
        elif delta.days < 365:
            changefreq = 'weekly'
            priority = 0.1
        else:
            changefreq = 'monthly'
            priority = 0.1

        items.append({
            'url': url_for('story.view', pk=story_id, _external=True),
            'lastmod': updated_at,
            'changefreq': changefreq,
            'priority': priority,
        })

    # Собираем ссылки на главы
    chapters = select(
        (x.story.id, x.order, x.first_published_at, x.updated) for x in Chapter
        if x.story.id in story_ids and not x.draft
    )[:]
    chapters.sort(key=lambda x: x[2], reverse=True)

    for story_id, chapter_order, first_published_at, updated_at in chapters:
        if updated_at < first_published_at:
            updated_at = first_published_at
        delta = now - first_published_at
        if delta.days < 1:
            changefreq = 'hourly'
            priority = 0.9
        elif delta.days < 14:
            changefreq = 'weekly'
            priority = 0.4
        else:
            changefreq = 'monthly'
            priority = 0.1

        items.append({
            'url': url_for('chapter.view', story_id=story_id, chapter_order=chapter_order, _external=True),
            'lastmod': updated_at,
            'changefreq': changefreq,
            'priority': priority,
        })

    return render_template('sitemap/urlset.xml', items=items)
