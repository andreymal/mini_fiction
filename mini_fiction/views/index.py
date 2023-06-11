#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session, desc

from mini_fiction.bl.migration import enrich_stories
from mini_fiction.models import Story, StoryContributor, StoryTag, Tag
from mini_fiction.utils.views import cached_lists
from mini_fiction.utils.misc import IndexPaginator, indextitle, sitedescription

bp = Blueprint('index', __name__)


@bp.route('/')
@db_session
def index():
    page_title = gettext('Index')

    stories = Story.select_published().filter(lambda x: not x.pinned)
    stories = stories.sort_by(desc(Story.first_published_at), desc(Story.id))
    stories = stories.prefetch(
        Story.characters, Story.contributors, StoryContributor.user,
        Story.tags, StoryTag.tag, Tag.category,
    )
    page_obj = IndexPaginator(
        1,
        total=stories.count(),
        per_page=current_app.config['STORIES_COUNT']['stream'],
    )
    stories = page_obj.slice(stories)

    pinned_stories = list(
        Story.select_published().filter(lambda x: x.pinned).sort_by(desc(Story.first_published_at))
    )
    stories = pinned_stories + list(stories)
    enrich_stories(stories)

    sidebar_blocks = []
    for block_name in current_app.config['INDEX_SIDEBAR_ORDER']:
        if isinstance(block_name, str):
            params = {}
        else:
            params = dict(block_name[1])
            block_name = block_name[0]

        block_html = current_app.index_sidebar[block_name](params)
        if block_html is not None:
            sidebar_blocks.append(block_html)

    data = {
        'stories': stories,
        'page_obj': page_obj,
        'page_title': page_title,
        'full_title': indextitle(),
        'site_description': sitedescription(),
        'sidebar_blocks': sidebar_blocks,
    }
    data.update(cached_lists([x.id for x in stories], chapter_view_dates=current_user.detail_view))

    return render_template('index.html', **data)
