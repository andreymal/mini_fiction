#!/usr/bin/env python
# -*- coding: utf-8 -*-

from queue import Queue
from threading import local

import MySQLdb


Error = MySQLdb.Error


class SphinxError(Exception):
    pass


class SphinxConnection(object):
    actions_list = {
        'lt': '`%s` < %%s',
        'lte': '`%s` <= %%s',
        'gt': '`%s` > %%s',
        'gte': '`%s` >= %%s',
        'eq': '`%s` = %%s',
        'ne': '`%s` <> %%s'
    }

    def __init__(self, conn):
        self.mysql_conn = MySQLdb.connect(**conn)
        self.mysql_conn.ping(True)
        self.execute('set autocommit=0')
        self._with_level = 0

    def __enter__(self):
        self._with_level += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        assert self._with_level > 0

        self._with_level -= 1
        if self._with_level == 0:
            if exc:
                if not isinstance(exc, Error) or exc.args[0] not in (2002, 2013):
                    self.rollback()
            else:
                self.commit()


    def execute(self, sql, args=None):
        if isinstance(sql, str):
            sql = sql.encode('utf-8')
        cursor = self.mysql_conn.cursor()
        cursor.execute(sql, tuple((x.encode('utf-8') if isinstance(x, str) else x) for x in args) if args else None)
        return cursor

    def build_where(self, filters):
        sql = ''
        args = []
        for f, x in filters.items():
            if '__' not in f:
                if sql:
                    sql += ' and '
                sql += '`%s` = %%s' % f
                args.append(x)
                continue

            f, action = f.rsplit('__', 1)

            if action == 'in':
                if x:
                    q, l = self.prepare_list(x)
                    if sql:
                        sql += ' and '
                    sql += '`%s` in %s' % (f, q)
                    args.extend(l)

            elif action == 'not_in':
                if x:
                    q, l = self.prepare_list(x)
                    if sql:
                        sql += ' and '
                    sql += '`%s` not in %s' % (f, q)
                    args.extend(l)

            elif action in self.actions_list:
                if sql:
                    sql += ' and '
                sql += self.actions_list[action] % f
                args.append(x)

            else:
                raise ValueError('Unknown action %r' % action)

        return sql, args

    def prepare_list(self, l):
        if not l:
            return '()', ()
        q = '(' + ('%s, ' * (len(l) - 1)) + '%s)'
        return q, l

    def escape_sphinxql(self, s):
        s = str(s)
        toreplace = [
            '\\', '(', ')', '|', '-', '!', '@', '~', '"', '&', '/', '^', '$', '=', '<',
            'OR', 'NOT', 'MAYBE', 'NEAR', 'SENTENCE', 'PARAGRAPH', 'ZONE', 'ZONESPAN',
        ]

        for c in toreplace:
            s = s.replace(c, '\\' + c)

        return s

    def search(
            self, index, query, fields=('id',), raw_fields=('WEIGHT() AS weight',),
            sort_by=None, limit=None, options=None, weights=None, extended_syntax=True,
            **filters
        ):
        # SELECT
        rfields = ', '.join('`%s`' % x for x in fields)
        if raw_fields:
            rfields = rfields + ', ' + ', '.join(raw_fields)
        sql = 'select %s from `%s` where match(%%s)' % (rfields, index)

        query = self.escape_sphinxql(query) if not extended_syntax else str(query)
        args = [query]

        # WHERE
        wsql = ''
        wargs = []
        if filters:
            wsql, wargs = self.build_where(filters)
        if wsql:
            sql += ' and ' + wsql
            args.extend(wargs)

        # ORDER
        if sort_by is not None:
            if isinstance(sort_by, (tuple, list)):
                sql += ' order by ' + ', '.join(sort_by)
            else:
                sql += ' order by ' + str(sort_by)

        # LIMIT
        if limit is not None:
            if isinstance(limit, int):
                sql += ' limit %d' % limit
            else:
                sql += ' limit %d, %d' % (limit[0], limit[1])

        # OPTION
        if options or weights:
            sql += ' option '

        if options:
            sql += ', '.join('%s=%s' % (k, str(v)) for k, v in options.items())
            if weights:
                sql += ', '

        if weights:
            sql += 'field_weights=(%s)' % ', '.join('%s=%s' % (k, str(v)) for k, v in weights.items())

        # execute
        try:
            cur = self.execute(sql, tuple(args))
        except MySQLdb.ProgrammingError as exc:
            if exc.args[0] != 1064:
                raise
            raise SphinxError(exc.args[1])
        fields = [x[0] for x in cur.description]
        matches = [dict(zip(fields, x)) for x in cur.fetchall()]

        cur.execute('show meta')
        result = dict(cur.fetchall())
        result['matches'] = matches
        return result

    def call_snippets(self, index, texts, query, **options):
        if isinstance(texts, str):
            texts = (texts,)
        sql = 'call snippets(('
        sql += ', '.join('%s' for _ in range(len(texts)))
        sql += '), %s, %s'
        args = list(texts + (index, query))

        for opt, value in options.items():
            sql += ', %%s as `%s`' % opt
            args.append(value)
        sql += ')'

        cur = self.execute(sql, tuple(args))
        return [x[0] for x in cur.fetchall()]

    def call_keywords(self, index, query, hits=False):
        sql = 'call keywords(%s, %s, %s)'
        args = [query, index, 1 if hits else 0]

        cur = self.execute(sql, args)
        result_fields = [x[0] for x in cur.description]
        result = [
            dict(zip(result_fields, x)) for x in cur.fetchall()
        ]
        return result

    def add(self, index, items):
        if not items:
            return
        fields = tuple(x[0] for x in items[0].items())
        sfields = ', '.join('`%s`' % x for x in fields)
        sql = ['replace into `%s` (%s) values ' % (index, sfields)]

        args = []

        first = True
        for item in items:
            if first:
                first = False
                isql = '('
            else:
                isql = ', ('

            ifirst = True
            for fk in fields:
                if ifirst:
                    ifirst = False
                else:
                    isql += ', '

                f = item[fk]
                if isinstance(f, (tuple, list)):
                    args.extend(f)
                    isql += '(' + ', '.join('%s' for _ in range(len(f))) + ')'
                else:
                    args.append(f)
                    isql += '%s'

            sql.append(isql + ')')

        self.execute(''.join(sql), tuple(args))

    def update(self, index, fields, **filters):
        sql = 'update `%s` set ' % index
        fields_list = tuple(fields.keys())
        if not fields_list:
            raise ValueError('Empty fields list is not allowed')
        sql += ', '.join(('`%s` = %%s' % f) for f in fields_list)
        args = list(fields[f] for f in fields_list)

        wsql = ''
        wargs = []
        if filters:
            wsql, wargs = self.build_where(filters)
        if wsql:
            sql += ' where ' + wsql
            args.extend(wargs)

        self.execute(sql, args)

    def delete(self, index, **filters):
        sql = 'delete from `%s`' % index
        args = []

        wsql = ''
        wargs = []
        if filters:
            wsql, wargs = self.build_where(filters)
        if wsql:
            sql += ' where ' + wsql
            args.extend(wargs)

        self.execute(sql, args)

    def begin(self):
        self.mysql_conn.begin()

    def commit(self):
        self.mysql_conn.commit()

    def rollback(self):
        self.mysql_conn.rollback()

    def flush(self, index):
        self.execute('flush rtindex `%s`' % index)


class SphinxPool(object):
    def __init__(self, conn, max_conns=5, conn_queue=None):
        self.conn = conn
        self.max_conns = max_conns
        self.count = 0
        self.local = local()
        self.conn_queue = conn_queue or Queue()

    def __enter__(self):
        if not hasattr(self.local, 'level') or self.local.level == 0:
            if self.conn_queue.empty() and self.count < self.max_conns:
                self.conn_queue.put(SphinxConnection(self.conn))
                self.count += 1
            self.local.conn = self.conn_queue.get()
            self.local.conn.__enter__()
            self.local.level = 1
        else:
            self.local.level += 1
        return self.local.conn

    def __exit__(self, exc_type=None, exc=None, tb=None):
        assert self.local.level > 0
        assert self.local.conn is not None

        self.local.level -= 1
        if self.local.level == 0:
            c = self.local.conn
            self.local.conn = None
            c.__exit__(exc_type, exc, tb)
            self.conn_queue.put(c)
