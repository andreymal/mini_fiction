#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import Story, Tag, StoryContributor, StoryTag
from mini_fiction.utils.views import cached_lists
from mini_fiction.utils.misc import Paginator, normalize_tag

bp = Blueprint('tags', __name__)


@bp.route('/tags/')
@db_session
def index():
    sort = request.args.get('sort')
    if sort not in ('stories', 'date', 'name'):
        sort = 'name'

    categories = Tag.bl.get_tags_with_categories(sort=sort)
    return render_template('tags/index.html', page_title='Теги', categories=categories, sort=sort)


@bp.route('/tag/<tag_name>/page/last/', defaults={'page': -1})
@bp.route('/tag/<tag_name>/', defaults={'page': 1})
@bp.route('/tag/<tag_name>/page/<int:page>/')
@db_session
def tag_index(tag_name, page):
    iname = normalize_tag(tag_name)
    tag = Tag.get(iname=iname)
    if not tag:
        abort(404)
    if iname != tag_name:
        return redirect(url_for('tags.tag_index', tag_name=iname, page=page))

    objects = Story.bl.select_by_tag(tag, user=current_user._get_current_object())
    objects = objects.prefetch(Story.characters, Story.contributors, StoryContributor.user, Story.tags, StoryTag.tag, Tag.category)
    objects = objects.order_by(Story.first_published_at.desc(), Story.id.desc())

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['STORIES_COUNT']['stream'])
    objects = page_obj.slice_or_404(objects)

    return render_template(
        'tags/tag_index.html',
        page_title=tag.name,
        tag=tag,
        aliases=[x.name for x in Tag.bl.get_aliases_for([tag])[tag.id]],
        category=tag.category,
        stories=objects,
        page_obj=page_obj,
        **cached_lists([x.id for x in objects])
    )


@bp.route('/tags/autocomplete.json')
@db_session
def autocomplete():
    tag_name = (request.args.get('tag') or '').strip()

    tags = []
    is_default = False
    data = None

    if len(tag_name) < 2:
        # Предложения по умолчанию, чтобы пусто не было
        # (кэшируются)
        is_default = True
        data = current_app.cache.get('tags_autocomplete_default')
        if not data:
            tags = _get_default_tags()

    else:
        tags = Tag.bl.search_by_prefix(tag_name)

    if not data:
        aliases = Tag.bl.get_aliases_for(tags)

        result = {
            'success': True,
            'tags': [{
                'id': tag.id,
                'name': tag.name,
                'url': url_for('tags.tag_index', tag_name=tag.iname),
                'description': tag.description,
                'stories_count': tag.published_stories_count,
                'aliases': [x.iname for x in aliases[tag.id]],
                'color': tag.get_color(),
            } for tag in tags],
        }
        data = json.dumps(result, ensure_ascii=False, sort_keys=True)
        if is_default:
            current_app.cache.set('tags_autocomplete_default', data, timeout=600)

    response = current_app.response_class(data, mimetype='application/json')
    response.headers['X-Robots-Tag'] = 'noindex'
    return response


def _get_default_tags(limit=20):
    tags = []
    all_tags = Tag.bl.get_all_tags()

    # В начале основные теги
    tags = [x for x in all_tags if x.is_main_tag]
    tags.sort(key=lambda x: (x.category.id if x.category else 2 ** 31, x.iname))

    # Потом двадцать самых популярных
    cnt = 0
    all_tags.sort(key=lambda x: x.published_stories_count, reverse=True)
    for x in all_tags:
        if not x.is_main_tag:
            tags.append(x)
            cnt += 1
            if cnt >= limit:
                break

    return tags
