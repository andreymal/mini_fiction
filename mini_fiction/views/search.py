#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from werkzeug.datastructures import ImmutableMultiDict
from flask import Blueprint, current_app, request, render_template
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

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


def search_form():
    form = SearchForm()
    data = {'form': form, 'page_title': gettext('Search of stories'), 'robots_noindex': True}
    return render_template('search.html', **data)


def search_action(postform):
    from mini_fiction.apis.amsphinxql import SphinxError

    if not postform.validate():
        data = {'form': postform, 'page_title': gettext('Search of stories'), 'robots_noindex': True}
        return render_template('search.html', **data)

    try:
        page_current = int(request.args.get('page') or 1)
    except Exception:
        page_current = 1

    query = postform.data['q']
    limit = ((page_current - 1) * current_app.config['SPHINX_CONFIG']['limit'], current_app.config['SPHINX_CONFIG']['limit'])
    search_type = postform.data['type']
    sort_type = postform.data['sort']

    data = {'page_title': query.strip() or gettext('Search results'), 'search_type': search_type, 'robots_noindex': True}

    if search_type == 0:
        if current_user.is_authenticated:
            excluded_categories = [x for x in current_user.excluded_categories_list if x not in postform.data['genre']]
        else:
            excluded_categories = []
        try:
            raw_result, result = Story.bl.search(
                query,
                limit,
                int(sort_type),
                only_published=not current_user.is_authenticated or not current_user.is_staff,
                extended_syntax=postform.data.get('extsyntax'),
                character=postform.data['char'],
                classifier=postform.data['cls'],
                category=postform.data['genre'],
                rating_id=postform.data['rating'],
                original=postform.data['original'],
                finished=postform.data['finished'],
                freezed=postform.data['freezed'],
                min_words=postform.data['min_words'],
                max_words=postform.data['max_words'],
                min_vote_total=current_app.config['MINIMUM_VOTES_FOR_VIEW'] if int(sort_type) == 3 else None,
                excluded_categories=excluded_categories,
            )
        except SphinxError as exc:
            data = {'form': postform, 'page_title': gettext('Search of stories'), 'error': 'Кажется, есть синтаксическая ошибка в запросе', 'error_type': 'syntax'}
            if current_app.config['DEBUG'] or current_user.is_superuser:
                data['error'] += ': ' + str(exc)
            return render_template('search.html', **data)

    else:
        try:
            raw_result, result = Chapter.bl.search(
                query,
                limit,
                int(sort_type),
                # TODO: сортировка и для глав тоже
                only_published=not current_user.is_authenticated or not current_user.is_staff,
                extended_syntax=postform.data.get('extsyntax'),
                character=postform.data['char'],
                classifier=postform.data['cls'],
                category=postform.data['genre'],
                rating_id=postform.data['rating'],
                original=postform.data['original'],
                finished=postform.data['finished'],
                freezed=postform.data['freezed'],
                min_words=postform.data['min_words'],
                max_words=postform.data['max_words'],
                min_vote_total=current_app.config['MINIMUM_VOTES_FOR_VIEW'] if int(sort_type) == 3 else None,
            )
        except SphinxError as exc:
            data = {'form': postform, 'page_title': gettext('Search of stories'), 'error': 'Кажется, есть синтаксическая ошибка в запросе', 'error_type': 'syntax'}
            if current_app.config['DEBUG'] or current_user.is_superuser:
                data['error'] += ': ' + str(exc)
            return render_template('search.html', **data)

    pagination = Paginator(number=page_current, total=int(raw_result['total'] or 0), per_page=current_app.config['SPHINX_CONFIG']['limit'])

    data['form'] = postform
    data['pagination'] = pagination
    data['total'] = int(raw_result['total_found'])
    data['result'] = result
    data['weights'] = [(x['id'], x['weight']) for x in raw_result['matches']]
    return render_template('search.html', **data)


@bp.route('/<search_type>/<int:search_id>/')
@db_session
def simple(search_type, search_id):
    if current_app.config['SPHINX_DISABLED']:
        return render_template('search_disabled.html', page_title=gettext('Search of stories'), robots_noindex=True)

    bound_data = {'type': '0', 'sort': '1'}
    if search_type == 'character':
        bound_data['char'] = [search_id]
    elif search_type == 'category':
        bound_data['genre'] = [search_id]
    elif search_type == 'classifier':
        bound_data['cls'] = [search_id]
    elif search_type == 'rating':
        bound_data['rating'] = [search_id]
    else:
        return search_form()

    postform = SearchForm(ImmutableMultiDict(bound_data))
    if postform.validate():
        return search_action(postform)
    return search_form()
