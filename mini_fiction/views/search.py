#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional

from werkzeug.datastructures import ImmutableMultiDict
from flask import Blueprint, current_app, request, render_template
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import cached_lists
from mini_fiction.forms.search import SearchForm
from mini_fiction.models import Story, Chapter
from mini_fiction.utils.misc import Paginator

bp = Blueprint('search', __name__)


@bp.route('/', methods=('GET',))
@db_session
def main():
    if current_app.config['SPHINX_DISABLED']:
        return render_template('search_disabled.html', page_title=gettext('Search of stories'), robots_noindex=True)

    postform = SearchForm(request.args, data={'type': 0, 'sort': 0})
    return search_action(postform)


def search_form(*, form: Optional[SearchForm] = None):
    data = {
        'form': form or SearchForm(),
        'page_title': gettext('Search of stories'),
        'robots_noindex': True,
    }
    return render_template('search.html', **data)


def search_action(postform):
    from mini_fiction.apis.amsphinxql import SphinxError

    if not postform.validate():
        return search_form(form=postform)

    try:
        page_current = int(request.args.get('page') or 1)
    except Exception:
        page_current = 1

    query = postform.data['q'] or ''
    limit = ((page_current - 1) * current_app.config['SPHINX_CONFIG']['limit'], current_app.config['SPHINX_CONFIG']['limit'])
    search_type = postform.data['type']
    sort_type = postform.data['sort']

    data = {
        'page_title': query.strip() or gettext('Search results'),
        'search_type': search_type,
        'robots_noindex': True,
        'story_weights': None,
        'chapter_weights': None,
    }

    story_results = None
    chapter_results = None

    if search_type == 0:
        try:
            story_results = Story.bl.search(
                query,
                limit,
                int(sort_type),
                only_published=not current_user.is_authenticated or not current_user.is_staff,
                extended_syntax=postform.data.get('extsyntax'),
                character=postform.data['char'],
                character_mode=postform.data['char_mode'],
                tags=postform.data.get('tags', []),
                tags_mode=postform.data['tags_mode'],
                exclude_tags=postform.data.get('exclude_tags', []),
                rating_id=postform.data['rating'],
                original=postform.data['original'],
                finished=postform.data['finished'],
                freezed=postform.data['freezed'],
                min_words=postform.data['min_words'],
                max_words=postform.data['max_words'],
                min_vote_total=current_app.config['MINIMUM_VOTES_FOR_VIEW'] if int(sort_type) == 3 else None,
            )
        except SphinxError as exc:
            data.update({'form': postform, 'page_title': gettext('Search of stories'), 'error': 'Кажется, есть синтаксическая ошибка в запросе', 'error_type': 'syntax'})
            if current_app.config['DEBUG'] or current_user.is_superuser:
                data['error'] += ': ' + str(exc)
            return render_template('search.html', **data)

        max_matches = story_results.total

    else:
        try:
            chapter_results = Chapter.bl.search(
                query,
                limit,
                int(sort_type),
                # TODO: сортировка и для глав тоже
                only_published=not current_user.is_authenticated or not current_user.is_staff,
                extended_syntax=postform.data.get('extsyntax'),
                character=postform.data['char'],
                character_mode=postform.data['char_mode'],
                tags=postform.data.get('tags', []),
                tags_mode=postform.data['tags_mode'],
                exclude_tags=postform.data.get('exclude_tags', []),
                rating_id=postform.data['rating'],
                original=postform.data['original'],
                finished=postform.data['finished'],
                freezed=postform.data['freezed'],
                min_words=postform.data['min_words'],
                max_words=postform.data['max_words'],
                min_vote_total=current_app.config['MINIMUM_VOTES_FOR_VIEW'] if int(sort_type) == 3 else None,
            )
        except SphinxError as exc:
            data.update({'form': postform, 'page_title': gettext('Search of stories'), 'error': 'Кажется, есть синтаксическая ошибка в запросе', 'error_type': 'syntax'})
            if current_app.config['DEBUG'] or current_user.is_superuser:
                data['error'] += ': ' + str(exc)
            return render_template('search.html', **data)

        max_matches = chapter_results.total

    if max_matches > 0:
        pagination = Paginator(
            number=page_current,
            total=max_matches,
            per_page=current_app.config['SPHINX_CONFIG']['limit'],
        )
    else:
        pagination = None

    data['form'] = postform
    data['pagination'] = pagination
    data['story_results'] = story_results
    data['chapter_results'] = chapter_results
    if story_results:
        data['story_weights'] = [(x['id'], x['weight']) for x in story_results.matches]
    if chapter_results:
        data['chapter_weights'] = [(x['id'], x['weight']) for x in chapter_results.matches]

    if search_type == 0:
        data.update(cached_lists([x.id for x in story_results.stories], chapter_view_dates=current_user.detail_view))
    else:
        data.update(cached_lists([x[0].story.id for x in chapter_results.chapters]))

    return render_template('search.html', **data)


@bp.route('/<search_type>/<int:search_id>/')
@db_session
def simple(search_type, search_id):
    if current_app.config['SPHINX_DISABLED']:
        return render_template('search_disabled.html', page_title=gettext('Search of stories'), robots_noindex=True)

    bound_data = {'type': '0', 'sort': '1'}
    if search_type == 'character':
        bound_data['char'] = [search_id]
    elif search_type == 'rating':
        bound_data['rating'] = [search_id]
    else:
        return search_form()

    postform = SearchForm(ImmutableMultiDict(bound_data))
    if postform.validate():
        return search_action(postform)
    return search_form()
