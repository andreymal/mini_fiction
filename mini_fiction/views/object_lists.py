#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import select, db_session
from flask import Blueprint, current_app, abort, render_template, request
from flask_login import current_user, login_required
from flask_babel import gettext, ngettext

from mini_fiction.models import Author, Story, StoryContributor, Favorites, Bookmark, StoryView, StoryTag, Tag
from mini_fiction.utils.misc import Paginator
from mini_fiction.utils.views import cached_lists


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

    page_obj = Paginator(page, objects.count(), per_page=10)
    stories = page_obj.slice_or_404(objects)

    data = dict(
        stories=stories,
        page_obj=page_obj,
        page_title=page_title,
        author=user,
    )
    data.update(cached_lists([x.id for x in stories]))

    return render_template('favorites.html', **data)


@bp.route('/submitted/page/last/', defaults={'page': -1})
@bp.route('/submitted/', defaults={'page': 1})
@bp.route('/submitted/page/<int:page>/')
@db_session
def submitted(page):
    if not current_user.is_staff:
        abort(403)
    objects = Story.select_submitted()
    page_obj = Paginator(page, objects.count(), per_page=10)
    stories = page_obj.slice_or_404(objects)

    data = dict(
        stories=stories,
        page_obj=page_obj,
        page_title='Новые поступления',
    )
    data.update(cached_lists([x.id for x in stories]))

    return render_template('submitted.html', **data)


@bp.route('/bookmarks/page/last/', defaults={'page': -1})
@bp.route('/bookmarks/', defaults={'page': 1})
@bp.route('/bookmarks/page/<int:page>/')
@db_session
@login_required
def bookmarks(page):
    objects = select(x.story for x in Bookmark if x.author.id == current_user.id).without_distinct().order_by('-x.id')
    page_obj = Paginator(page, objects.count(), per_page=10)
    stories = page_obj.slice_or_404(objects)

    data = dict(
        stories=stories,
        page_obj=page_obj,
        page_title='Прочитать позже',
    )
    data.update(cached_lists([x.id for x in stories]))

    return render_template('bookmarks.html', **data)


@bp.route('/viewed/page/last/', defaults={'page': -1})
@bp.route('/viewed/', defaults={'page': 1})
@bp.route('/viewed/page/<int:page>/')
@db_session
@login_required
def viewed(page):
    views = select(
        (x.story, min(x.id)) for x in StoryView if x.author.id == current_user.id and x.story
    )
    views = views.prefetch(StoryView.story, Story.characters, Story.contributors, StoryContributor.user, Story.tags, StoryTag.tag, Tag.category)
    views = views.order_by(-2)

    page_obj = Paginator(page, views.count(), per_page=10)

    stories = [x[0] for x in page_obj.slice_or_404(views)]

    return render_template(
        'viewed.html',
        stories=stories,
        page_obj=page_obj,
        page_title='Просмотренные рассказы',
        stories_detail_view=True,
        **cached_lists([x.id for x in stories])
    )


@bp.route('/story/top/page/last/', defaults={'page': -1})
@bp.route('/story/top/', defaults={'page': 1})
@bp.route('/story/top/page/<int:page>/')
@db_session
def top(page):
    period = request.args.get('period')
    if period and period.isdigit():
        period = int(period)
    else:
        period = 0

    objects = Story.bl.select_top(period)
    objects = objects.prefetch(Story.characters, Story.contributors, StoryContributor.user, Story.tags, StoryTag.tag, Tag.category)

    page_obj = Paginator(
        page,
        objects.count(),
        per_page=current_app.config['STORIES_COUNT']['stream'],
        view_args={'period': period} if period > 0 else None,
    )

    stories = page_obj.slice_or_404(objects)

    if period == 7:
        page_title = gettext('Top stories for the week')
    elif period == 30:
        page_title = gettext('Top stories for the month')
    elif period == 365:
        page_title = gettext('Top stories for the year')
    elif period == 0:
        page_title = gettext('Top stories for all time')
    else:
        page_title = ngettext('Top stories in %(num)d day', 'Top stories in %(num)d days', period)

    data = dict(
        stories=stories,
        page_obj=page_obj,
        count=objects.count(),
        page_title=page_title,
        period=period,
    )
    data.update(cached_lists([x.id for x in stories]))

    return render_template('stream/stories_top.html', **data)
