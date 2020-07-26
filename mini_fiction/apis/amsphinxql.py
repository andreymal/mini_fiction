#!/usr/bin/env python
# -*- coding: utf-8 -*-

from queue import Queue
from threading import local


match_operators_list = [
    "\\", "(", ")", "|", "-", "!", "@", "~", '"', "&", "/", "^", "$", "=", "<",
    "OR", "NOT", "MAYBE", "NEAR", "NOTNEAR", "SENTENCE", "PARAGRAPH", "ZONE",
    "ZONESPAN",
]


class SphinxError(Exception):
    pass


class SphinxConnection:
    actions_list = {
        'lt': '`%s` < %%s',
        'lte': '`%s` <= %%s',
        'gt': '`%s` > %%s',
        'gte': '`%s` >= %%s',
        'eq': '`%s` = %%s',
        'ne': '`%s` <> %%s',
    }

    def __init__(self, conn):
        # Ленивая загрузка MySQLdb ради поддержки pymysql.install_as_MySQLdb()
        import MySQLdb
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
                from MySQLdb import Error
                # 2002 - Can't connect to local MySQL server
                # 2013 - Lost connection to MySQL server during query
                if not isinstance(exc, Error) or exc.args[0] not in (2002, 2013):
                    self.rollback()
            else:
                self.commit()

    def execute(self, sql, args=None):
        coded_sql = sql.encode('utf-8') if isinstance(sql, str) else sql

        coded_args = None
        if args:
            coded_args = tuple((x.encode('utf-8') if isinstance(x, str) else x) for x in args)

        cursor = self.mysql_conn.cursor()
        cursor.execute(coded_sql, coded_args)
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

            if action in ('in', 'in_any'):
                if x:
                    q, l = self.prepare_sql_list(x)
                    if sql:
                        sql += ' and '
                    sql += '`%s` in %s' % (f, q)
                    args.extend(l)

            elif action == 'in_all':
                if x:
                    for v in x:
                        if sql:
                            sql += ' and '
                        sql += '`%s` = %%s' % f
                        args.append(v)

            elif action == 'not_in':
                if x:
                    q, l = self.prepare_sql_list(x)
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

    @classmethod
    def prepare_sql_list(cls, l):
        if not l:
            return '()', ()
        q = '(' + ('%s, ' * (len(l) - 1)) + '%s)'
        return q, l

    @classmethod
    def escape_match(cls, s):
        s = str(s)
        for c in match_operators_list:
            s = s.replace(c, '\\' + c)

        return s

    def build_search_sql(
            self,
            index,  # type: str
            query,  # type: str
            fields=('id',),  # type: Iterable[str]
            raw_fields=('WEIGHT() AS weight',),  # type: Iterable[str]
            sort_by=None,  # type: Optional[str]
            limit=None,  # type: Union[None, int, Tuple[int, int]]
            options=None,  # type: Optional[Dict[str, Any]]
            weights=None,  # type: Optional[Dict[str, Any]]
            extended_syntax=True,  # type: bool
            **filters  # type: Any
        ):
        # type: (...) -> Tuple[str, Tuple[Any, ...]]

        # SELECT
        sql_fields = ['`%s`' % x for x in fields]
        if raw_fields:
            sql_fields.extend(raw_fields)
        sql = 'select %s from `%s` where match(%%s)' % (', '.join(sql_fields) or '1', index)

        query = self.escape_match(query) if not extended_syntax else str(query)
        args = [query]

        # WHERE
        if 'filters' in filters:
            # support filters={'field__eq': '...'}
            filters = filters['filters']
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

        return sql, tuple(args)

    def search(
            self,
            index,  # type: str
            query,  # type: str
            fields=('id',),  # type: Iterable[str]
            raw_fields=('WEIGHT() AS weight',),  # type: Iterable[str]
            sort_by=None,  # type: Optional[str]
            limit=None,  # type: Union[None, int, Tuple[int, int]]
            options=None,  # type: Optional[Dict[str, Any]]
            weights=None,  # type: Optional[Dict[str, Any]]
            extended_syntax=True,  # type: bool
            **filters  # type: Any
        ):
        # type: (...) -> Dict[str, Any]

        from MySQLdb import ProgrammingError

        sql, args = self.build_search_sql(
            index, query, fields, raw_fields, sort_by, limit, options, weights,
            extended_syntax, **filters
        )

        # execute
        try:
            cur = self.execute(sql, tuple(args))
        except ProgrammingError as exc:
            if exc.args[0] != 1064:  # error in SQL syntax
                raise
            raise SphinxError(exc.args[1])
        result_fields = [x[0] for x in cur.description]
        matches = [dict(zip(result_fields, x)) for x in cur.fetchall()]

        cur.execute('show meta')
        result = dict(cur.fetchall())
        result['matches'] = matches
        return result

    def call_snippets(self, index, texts, query, **options):
        if isinstance(texts, str):
            texts = [texts]
        else:
            texts = list(texts)
        if not texts:
            return []
        sql = 'call snippets(('
        sql += ', '.join('%s' for _ in range(len(texts)))
        sql += '), %s, %s'
        args = texts + [index, query]

        for opt, value in options.items():
            sql += ', %%s as `%s`' % opt
            args.append(value)
        sql += ')'

        cur = self.execute(sql, args)
        return [str(x[0]) for x in cur.fetchall()]

    def call_keywords(self, index, query, hits=False):
        sql = 'call keywords(%s, %s, %s)'
        args = [query, index, 1 if hits else 0]

        cur = self.execute(sql, args)
        result_fields = [x[0] for x in cur.description]
        result = [
            dict(zip(result_fields, x)) for x in cur.fetchall()
        ]
        return result

    def build_add_sql(self, index, items, replace=True):
        if not items:
            return '', ()

        fields = tuple(x[0] for x in items[0].items())
        sfields = ', '.join('`%s`' % x for x in fields)
        sql = [
            'replace' if replace else 'insert',
            ' into `%s` (%s) values ' % (index, sfields),
        ]

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
                if isinstance(f, (tuple, list, set, frozenset)):
                    # rt_attr_multi
                    args.extend(f)
                    isql += '(' + ', '.join('%s' for _ in range(len(f))) + ')'
                else:
                    args.append(f)
                    isql += '%s'

            sql.append(isql + ')')

        return ''.join(sql), tuple(args)

    def add(self, index, items, replace=True):
        sql, args = self.build_add_sql(index, items, replace=replace)
        if sql:
            self.execute(sql, args)

    def build_update_sql(self, index, fields, **filters):
        sql = 'update `%s` set ' % index
        fields_list = tuple(fields.keys())
        if not fields_list:
            raise ValueError('Empty fields list is not allowed')
        sql += ', '.join(('`%s` = %%s' % f) for f in fields_list)
        args = list(fields[f] for f in fields_list)

        if 'filters' in filters:
            # support filters={'field__eq': '...'}
            filters = filters['filters']
        if filters:
            wsql, wargs = self.build_where(filters)
            if wsql:
                sql += ' where ' + wsql
                args.extend(wargs)

        return sql, tuple(args)

    def update(self, index, fields, **filters):
        sql, args = self.build_update_sql(index, fields, **filters)
        self.execute(sql, args)

    def build_delete_sql(self, index, **filters):
        sql = 'delete from `%s`' % index
        args = []

        if 'filters' in filters:
            # support filters={'field__eq': '...'}
            filters = filters['filters']
        if filters:
            wsql, wargs = self.build_where(filters)
            if wsql:
                sql += ' where ' + wsql
                args.extend(wargs)

        return sql, tuple(args)

    def delete(self, index, **filters):
        sql, args = self.build_delete_sql(index, **filters)
        self.execute(sql, args)

    def begin(self):
        self.mysql_conn.begin()

    def commit(self):
        self.mysql_conn.commit()

    def rollback(self):
        self.mysql_conn.rollback()

    def flush(self, index):
        self.execute('flush rtindex `%s`' % index)


class SphinxPool:
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
