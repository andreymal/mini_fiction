#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading

from flask import current_app, abort, json_available, g
from flask_debugtoolbar import module
from flask_debugtoolbar.panels import DebugPanel
import itsdangerous

from pony.orm import db_session
from mini_fiction.database import db


_ = lambda x: x

local = threading.local()


def record_query(query):
    if not hasattr(local, 'queries'):
        local.queries = []
    local.queries.append(query)


def clear_queries():
    if hasattr(local, 'queries'):
        del local.queries


def query_signer():
    return itsdangerous.URLSafeSerializer(current_app.config['SECRET_KEY'],
                                          salt='fdt-sql-query')


def format_sql(sql, arguments=None):
    if not arguments:
        return sql
    return '{} -- {}'.format(sql, arguments)


def is_select(statement):
    prefix = b'select' if isinstance(statement, bytes) else 'select'
    return statement.lower().strip().startswith(prefix)


def dump_query(statement, params):
    if not params or not is_select(statement):
        return None

    try:
        return query_signer().dumps([statement, params])
    except TypeError:
        return None


def load_query(data):
    try:
        statement, params = query_signer().loads(request.args['query'])
    except (itsdangerous.BadSignature, TypeError):
        abort(406)

    # Make sure it is a select statement
    if not is_select(statement):
        abort(406)

    return statement, params


def recording_enabled():
    return current_app.debug or current_app.config.get('PONYORM_RECORD_QUERIES')


def is_available():
    return json_available and recording_enabled()


def get_queries():
    return getattr(local, 'queries', [])


class PonyDebugPanel(DebugPanel):
    name = 'Pony'

    @property
    def has_content(self):
        return bool(get_queries()) or not is_available()

    def process_request(self, request):
        pass

    def process_response(self, request, response):
        pass

    def nav_title(self):
        return _('Pony ORM')

    def nav_subtitle(self):
        count = len(get_queries())

        if not count and not is_available():
            return 'Unavailable'

        return '%d %s' % (count, 'query' if count == 1 else 'queries')

    def title(self):
        return _('Pony ORM queries')

    def url(self):
        return ''

    def content(self):
        queries = get_queries()

        if not queries and not is_available():
            return self.render('panels/sqlalchemy_error.html', {
                'json_available': json_available,
                'sqlalchemy_available': True,
                'extension_used': True,
                'recording_enabled': recording_enabled(),
            })

        data = []
        for query in queries:
            data.append({
                'duration': query['duration'],
                'sql': format_sql(query['statement'], query['parameters']),
                'signed_query': dump_query(query['statement'], query['parameters']),
                'context_long': '',  # TODO: query.context,
                'context': '',  # TODO: format_fname(query.context)
            })
        return self.render('panels/sqlalchemy.html', {'queries': data})

# Panel views


@module.route('/sqlalchemy/sql_select', methods=['GET', 'POST'])
@module.route('/sqlalchemy/sql_explain', methods=['GET', 'POST'],
              defaults=dict(explain=True))
@db_session
def sql_select(explain=False):
    from flask import request

    statement, params = load_query(request.args['query'])

    if explain:
        if False and current_app.config.get('DATABASE_ENGINE') == 'sqlite':
            statement = 'EXPLAIN QUERY PLAN\n%s' % statement
        else:
            statement = 'EXPLAIN\n%s' % statement

    result = db._exec_sql(statement, tuple(params), False, False)

    headers = [x[0] for x in result.description]  # TODO: check with non-sqlite3 and non-mysql

    return g.debug_toolbar.render('panels/sqlalchemy_select.html', {
        'result': result.fetchall(),
        'headers': headers,
        'sql': format_sql(statement, params),
        'duration': float(request.args['duration']),
    })
