#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from pony.orm import select, db_session
from flask import Blueprint, current_app, abort, render_template, request
from flask_login import current_user, login_required

from mini_fiction.models import Author, Story, StoryContributor, Favorites, Bookmark, StoryView
from mini_fiction.utils.misc import Paginator
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

    objects = select(x.story for x in Favorites if x.author == user)
    if not current_user.is_authenticated or (not current_user.is_staff and current_user.id != user.id):
        objects = objects.filter(lambda story: not story.draft and story.approved)
    objects = objects.without_distinct().order_by('-x.id')

    if current_user.is_authenticated and user.id == current_user.id:
        page_title = 'Мое избранное'
    else:
        page_title = 'Избранное автора %s' % user.username

    return paginate_view(
        'favorites.html',
        objects,
        count=objects.count(),
        page_title=page_title,
        author=user,
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
        page_title='Прочитать позже',
        objlistname='stories',
    )


@bp.route('/viewed/page/last/', defaults={'page': -1})
@bp.route('/viewed/', defaults={'page': 1})
@bp.route('/viewed/page/<int:page>/')
@db_session
@login_required
def viewed(page):
    views = select(
        (x.story, min(x.id)) for x in StoryView if x.author.id == current_user.id and x.story
    )
    views = views.prefetch(StoryView.story, Story.characters, Story.categories, Story.contributors, StoryContributor.user)
    views = views.order_by(-2)

    page_obj = Paginator(page, views.count(), per_page=10)

    stories = [x[0] for x in page_obj.slice_or_404(views)]

    return render_template(
        'viewed.html',
        stories=stories,
        page_obj=page_obj,
        page_title='Просмотренные рассказы',
        stories_detail_view=True,
    )


@bp.route('/story/top/page/last/', defaults={'page': -1})
@bp.route('/story/top/', defaults={'page': 1})
@bp.route('/story/top/page/<int:page>/')
@db_session
def top(page):
    objects = Story.select_published().filter(lambda x: x.vote_total >= current_app.config['MINIMUM_VOTES_FOR_VIEW'])

    period = request.args.get('period')
    if period and period.isdigit():
        period = int(period)
    else:
        period = 0

    if period > 0:
        since = datetime.utcnow() - timedelta(days=period)
        objects = objects.filter(lambda x: x.first_published_at >= since)

    objects = objects.order_by(Story.vote_value.desc(), Story.id.desc())
    objects = objects.prefetch(Story.characters, Story.categories, Story.contributors, StoryContributor.user)

    page_obj = Paginator(
        page,
        objects.count(),
        per_page=current_app.config['STORIES_COUNT']['stream'],
        view_args={'period': period} if period > 0 else None,
    )

    stories = page_obj.slice_or_404(objects)

    data = dict(
        stories=stories,
        page_obj=page_obj,
        count=objects.count(),
        page_title='Топ рассказов',
        period=period,
    )
    data.update(cached_lists([x.id for x in stories]))

    return render_template('stream/stories_top.html', **data)
