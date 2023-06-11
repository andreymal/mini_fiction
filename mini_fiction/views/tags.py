#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for
from flask_login import current_user
from pony.orm import db_session, desc

from mini_fiction.bl.migration import enrich_stories
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
    if not iname:
        abort(404)
    tag = Tag.get(iname=iname)
    if tag and tag.is_alias_for is not None:
        if tag.is_alias_for.is_alias_for:
            raise RuntimeError('Tag alias {} refers to another alias {}!'.format(tag.id, tag.is_alias_for.id))
        tag = tag.is_alias_for
    if not tag or tag.is_blacklisted:
        abort(404)
    if tag.iname != tag_name:
        return redirect(url_for('tags.tag_index', tag_name=tag.iname, page=page))

    objects = Story.bl.select_by_tag(tag, user=current_user)
    objects = objects.prefetch(Story.characters, Story.contributors, StoryContributor.user, Story.tags, StoryTag.tag, Tag.category)
    objects = objects.sort_by(desc(Story.first_published_at), desc(Story.id))

    page_obj = Paginator(page, objects.count(), per_page=current_app.config['STORIES_COUNT']['tags'])
    objects = page_obj.slice_or_404(objects)

    enrich_stories(objects)

    return render_template(
        'tags/tag_index.html',
        page_title=tag.name,
        tag=tag,
        aliases=[x.name for x in Tag.bl.get_aliases_for([tag])[tag.id]],
        category=tag.category,
        stories=objects,
        page_obj=page_obj,
        **cached_lists([x.id for x in objects], chapter_view_dates=current_user.detail_view)
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
            tags = get_default_tags_for_autocomplete()

    else:
        tags = Tag.bl.search_by_prefix(tag_name)

    if not data:
        data = build_tags_autocomplete_json(tags)
        data['success'] = True
        data = json.dumps(data, ensure_ascii=False, sort_keys=True)
        if is_default:
            current_app.cache.set('tags_autocomplete_default', data, timeout=600)

    response = current_app.response_class(data, mimetype='application/json')
    response.headers['X-Robots-Tag'] = 'noindex'
    return response


def build_tags_autocomplete_json(tags=None):
    if tags is None:
        tags = get_default_tags_for_autocomplete()
    aliases = Tag.bl.get_aliases_for(tags, hidden=True)

    result = {
        'tags': [{
            'id': tag.id,
            'name': tag.name,
            'url': url_for('tags.tag_index', tag_name=tag.iname),
            'is_spoiler': tag.is_spoiler,
            'description': tag.description,
            'stories_count': tag.published_stories_count,
            'aliases': [x.iname for x in aliases[tag.id]],
            'category_id': tag.category.id if tag.category else 0,
        } for tag in tags],
    }

    return result


def get_default_tags_for_autocomplete():
    # Отдаём все теги, отсортированные по популярности
    tags = list(Tag.bl.get_all_tags())
    tags.sort(key=lambda x: x.published_stories_count, reverse=True)
    return tags
