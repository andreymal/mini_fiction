#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template, abort, redirect, url_for
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import Story, Tag, StoryContributor, StoryTag
from mini_fiction.utils.views import cached_lists
from mini_fiction.utils.misc import Paginator, normalize_tag

bp = Blueprint('tags', __name__)


@bp.route('/tags/')
@db_session
def index():
    categories = Tag.bl.get_tags_with_categories()
    return render_template('tags/index.html', page_title='Теги', categories=categories)


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
