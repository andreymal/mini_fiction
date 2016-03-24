#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import select, db_session
from flask import Blueprint, current_app, abort
from flask_login import current_user, login_required

from mini_fiction.models import Author, Story, CoAuthorsStory, Favorites, Bookmark
from mini_fiction.utils.views import paginate_view, cached_lists


bp = Blueprint('object_lists', __name__)


@bp.route('/accounts/<int:user_id>/favorites/page/last/', defaults={'page': -1})
@bp.route('/accounts/<int:user_id>/favorites/', defaults={'page': 1})
@bp.route('/accounts/<int:user_id>/favorites/page/<int:page>/')
@db_session
def favorites(user_id, page):
    user = Author.get(id=user_id)
    if not user:
        abort(404)

    objects = select(x.story for x in Favorites if x.author == user).without_distinct().order_by('-x.id')

    if current_user.is_authenticated and user.id == current_user.id:
        page_title = 'Мое избранное'
    else:
        page_title = 'Избранное автора %s' % user.username

    return paginate_view(
        'favorites.html',
        objects,
        count=objects.count(),
        page_title=page_title,
        objlistname='stories',
    )


@bp.route('/submitted/page/last/', defaults={'page': -1})
@bp.route('/submitted/', defaults={'page': 1})
@bp.route('/submitted/page/<int:page>/')
@db_session
def submitted(page):
    if not current_user.is_staff:
        abort(403)
    objects = Story.select_submitted()

    return paginate_view(
        'submitted.html',
        objects,
        count=objects.count(),
        page_title='Новые поступления',
        objlistname='stories',
    )


@bp.route('/bookmarks/page/last/', defaults={'page': -1})
@bp.route('/bookmarks/', defaults={'page': 1})
@bp.route('/bookmarks/page/<int:page>/')
@db_session
@login_required
def bookmarks(page):
    objects = select(x.story for x in Bookmark if x.author.id == current_user.id).without_distinct().order_by('-x.id')

    return paginate_view(
        'bookmarks.html',
        objects,
        count=objects.count(),
        page_title='Закладки',
        objlistname='stories',
    )


@bp.route('/story/top/page/last/', defaults={'page': -1})
@bp.route('/story/top/', defaults={'page': 1})
@bp.route('/story/top/page/<int:page>/')
@db_session
def top(page):
    objects = Story.select_published().filter(lambda x: x.vote_total >= current_app.config['STARS_MINIMUM_VOTES'])
    objects = objects.order_by(Story.vote_average.desc(), Story.id.desc())
    objects = objects.prefetch(Story.characters, Story.categories, Story.coauthors, CoAuthorsStory.author)
    return paginate_view(
        'stream/stories.html',
        objects,
        count=objects.count(),
        page_title='Топ рассказов',
        objlistname='stories',
        per_page=current_app.config['STORIES_COUNT']['stream'],
        extra_context=lambda stories, _: cached_lists([x.id for x in stories])
    )
