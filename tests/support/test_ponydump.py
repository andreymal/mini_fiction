#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

import io
import os
import gzip
import uuid
import shutil
from datetime import datetime

import pytest
from pony import orm

from mini_fiction import ponydump
from mini_fiction.ponydump import PonyDump


testdb = orm.Database()
testdb_started = False


class PDTest1(testdb.Entity):
    k1 = orm.Required(int)
    k2 = orm.Required(int)
    k3 = orm.Required(int)
    test2 = orm.Optional('PDTest2')
    test3 = orm.Set('PDTest3')
    test4 = orm.Optional('PDTest4')
    orm.PrimaryKey(k1, k2, k3)


class PDTest2(testdb.Entity):
    test1 = orm.Required(PDTest1)


class PDTest3(testdb.Entity):
    test1 = orm.Optional(PDTest1)
    foo_bool = orm.Optional(bool, nullable=True, default=None)
    foo_int = orm.Required(int)
    foo_float = orm.Required(float)
    foo_string = orm.Required(str, 16)
    foo_longstr = orm.Required(orm.LongStr)
    foo_datetime = orm.Required(datetime)
    foo_uuid = orm.Required(uuid.UUID)


class PDTest4(testdb.Entity):
    test1 = orm.Optional(PDTest1)


class Many1(testdb.Entity):
    many2 = orm.Set('Many2')


class Many2(testdb.Entity):
    many1 = orm.Set(Many1)


@pytest.fixture(scope="function")
def use_testdb():
    global testdb_started
    if not testdb_started:
        testdb.bind('sqlite', ':memory:')
        testdb.generate_mapping(create_tables=True)
        testdb_started = True

    try:
        yield
    finally:
        testdb.rollback()

        # Workaround for some commit() calls
        conn = testdb.provider.pool.con
        if conn:
            conn.execute('PRAGMA foreign_keys = OFF')
            conn.execute('BEGIN TRANSACTION')
            for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                conn.execute('DELETE FROM {}'.format(x[0]))
            conn.execute('COMMIT')
            testdb.disconnect()


@pytest.fixture(scope="function")
def dumpdir(app):
    path1 = os.path.join(app.config['TESTING_DIRECTORY'], 'dumpfoo')
    assert not os.path.exists(path1)
    path = os.path.join(path1, 'dump')

    try:
        yield path
    finally:
        if os.path.exists(path1):
            shutil.rmtree(path1)


def _fill_testdb():
    test1 = PDTest1(k1=1, k2=2, k3=3)
    test1.flush()
    PDTest1(k1=3, k2=5, k3=6).flush()
    PDTest1(k1=4, k2=5, k3=5).flush()

    PDTest2(test1=test1).flush()

    PDTest3(
        test1=test1,
        foo_bool=True,
        foo_int=-4,
        foo_float=0.1 + 0.2,
        foo_string='foo\u0000😊bar',
        foo_longstr='longstr',
        foo_datetime=datetime(2017, 6, 1, 1, 2, 3, 999987),
        foo_uuid=uuid.UUID('8e8cdc11-0785-43a8-8203-66c148c3f57c'),
    )
    PDTest3(
        test1=test1,
        foo_bool=False,
        foo_int=4,
        foo_float=0.1 + 0.2,
        foo_string='foo\u0000😊bar',
        foo_longstr='longstr',
        foo_datetime=datetime(2017, 6, 1, 1, 2, 3, 999987),
        foo_uuid=uuid.UUID('8e8cdc11-0785-43a8-8203-66c148c3f57c'),
    )
    PDTest3(
        test1=None,
        foo_bool=None,
        foo_int=2**31 - 1,
        foo_float=0.0,
        foo_string='string',
        foo_longstr='string',
        foo_datetime=datetime(1970, 1, 1, 0, 0, 0),
        foo_uuid=uuid.UUID('8e8cdc11-0785-43a8-8203-66c148c3f57c'),
    )

    m1_1 = Many1()
    m1_1.flush()
    m1_2 = Many1()
    m1_2.flush()
    m2_1 = Many2()
    m2_1.flush()
    m2_2 = Many2()
    m2_2.flush()

    m1_1.many2 = [m2_1, m2_2]
    m1_2.many2 = [m2_1, m2_2]

    # PDTest4 не создаём, тестируем пустоту


def _opendump(dumpdir, name):
    path = os.path.join(dumpdir, name)
    if not os.path.isfile(path):
        path += '.gz'
        return gzip.open(path, 'rt', encoding='utf-8')
    return open(path, 'r', encoding='utf-8')


def _check_dump_content(dumpdir, name, data):
    data = list(reversed(data))
    with _opendump(dumpdir, name) as fp:
        for line in fp:
            assert line == data.pop()


# dumpdb tests


@pytest.mark.nodbcleaner
@pytest.mark.parametrize('gzip_compression', [0, 1])
@orm.db_session
def test_dump_to_directory_full(use_testdb, dumpdir, gzip_compression):
    pd = PonyDump(testdb)
    _fill_testdb()

    # Порядок дампа строго не определён
    dump_statuses = [
        {'current': 1, 'count': 2, 'pk': (1,), 'entity': 'many1', 'chunk_size': 250},
        {'current': 2, 'count': 2, 'pk': (2,), 'entity': 'many1', 'chunk_size': 250},
        {'current': 2, 'count': 2, 'pk': None, 'entity': 'many1', 'chunk_size': 250},

        {'current': 1, 'count': 2, 'pk': (1,), 'entity': 'many2', 'chunk_size': 250},
        {'current': 2, 'count': 2, 'pk': (2,), 'entity': 'many2', 'chunk_size': 250},
        {'current': 2, 'count': 2, 'pk': None, 'entity': 'many2', 'chunk_size': 250},

        {'current': 1, 'count': 3, 'pk': (1, 2, 3), 'entity': 'pdtest1', 'chunk_size': 250},
        {'current': 1, 'count': 3, 'pk': (1, 2, 3), 'entity': 'pdtest1', 'chunk_size': 250},
        {'current': 3, 'count': 3, 'pk': (4, 5, 5), 'entity': 'pdtest1', 'chunk_size': 250},
        {'current': 3, 'count': 3, 'pk': None, 'entity': 'pdtest1', 'chunk_size': 250},

        {'current': 1, 'count': 3, 'pk': (1,), 'entity': 'pdtest3', 'chunk_size': 250},
        {'current': 3, 'count': 3, 'pk': (3,), 'entity': 'pdtest3', 'chunk_size': 250},
        {'current': 3, 'count': 3, 'pk': None, 'entity': 'pdtest3', 'chunk_size': 250},

        {'current': 1, 'count': 1, 'pk': (1,), 'entity': 'pdtest2', 'chunk_size': 250},
        {'current': 1, 'count': 1, 'pk': (1,), 'entity': 'pdtest2', 'chunk_size': 250},
        {'current': 1, 'count': 1, 'pk': None, 'entity': 'pdtest2', 'chunk_size': 250},

        {'current': 0, 'count': 0, 'pk': None, 'entity': 'pdtest4', 'chunk_size': 250},

        {'entity': None, 'path': None, 'current': 0, 'count': 0, 'pk': None},  # Всегда последний
    ]

    filenames = [
        'pdtest1_dump.jsonl',
        'pdtest2_dump.jsonl',
        'pdtest3_dump.jsonl',
        'pdtest4_dump.jsonl',
        'many1_dump.jsonl',
        'many2_dump.jsonl',
    ]
    if gzip_compression:
        filenames = [x + '.gz' for x in filenames]
    filenames = set(filenames)

    # Проверка информацирования о процессе дампа
    for status in pd.dump_to_directory(dumpdir, gzip_compression=gzip_compression):
        path = status.pop('path')

        if path is not None:
            assert os.path.split(path)[1] in filenames
            assert os.path.isfile(path)
        else:
            status['path'] = path  # Для проверки последнего элемента

        assert status in dump_statuses
        dump_statuses.remove(status)

        if path is None:
            assert not dump_statuses

    assert not dump_statuses

    assert set(os.listdir(dumpdir)) == filenames

    # Проверка содержимого дампов:
    # - ключи у JSON отсортированы
    # - после запятых и двоеточий пробелы
    # - Файлы в UTF-8 без BOM
    # - перенос строк с помощью \n
    # - объекты внутри дампа отсортированы по первичным ключам
    _check_dump_content(dumpdir, 'pdtest1_dump.jsonl', [
        '{"_entity": "pdtest1", "k1": 1, "k2": 2, "k3": 3, "test2": 1, "test3": [1, 2], "test4": null}\n',
        '{"_entity": "pdtest1", "k1": 3, "k2": 5, "k3": 6, "test2": null, "test3": [], "test4": null}\n',
        '{"_entity": "pdtest1", "k1": 4, "k2": 5, "k3": 5, "test2": null, "test3": [], "test4": null}\n',
    ])

    _check_dump_content(dumpdir, 'pdtest2_dump.jsonl', [
        '{"_entity": "pdtest2", "id": 1, "test1": [1, 2, 3]}\n',
    ])

    _check_dump_content(dumpdir, 'pdtest3_dump.jsonl', [
        '{"_entity": "pdtest3", "foo_bool": true, "foo_datetime": "2017-06-01T01:02:03.999987Z", "foo_float": 0.30000000000000004, "foo_int": -4, "foo_longstr": "longstr", "foo_string": "foo\\u0000😊bar", "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c", "id": 1, "test1": [1, 2, 3]}\n',
        '{"_entity": "pdtest3", "foo_bool": false, "foo_datetime": "2017-06-01T01:02:03.999987Z", "foo_float": 0.30000000000000004, "foo_int": 4, "foo_longstr": "longstr", "foo_string": "foo\\u0000😊bar", "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c", "id": 2, "test1": [1, 2, 3]}\n',
        '{"_entity": "pdtest3", "foo_bool": null, "foo_datetime": "1970-01-01T00:00:00.000000Z", "foo_float": 0.0, "foo_int": 2147483647, "foo_longstr": "string", "foo_string": "string", "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c", "id": 3, "test1": null}\n',
    ])

    _check_dump_content(dumpdir, 'pdtest4_dump.jsonl', [''])

    _check_dump_content(dumpdir, 'many1_dump.jsonl', [
        '{"_entity": "many1", "id": 1, "many2": [1, 2]}\n',
        '{"_entity": "many1", "id": 2, "many2": [1, 2]}\n',
    ])

    _check_dump_content(dumpdir, 'many2_dump.jsonl', [
        '{"_entity": "many2", "id": 1, "many1": [1, 2]}\n',
        '{"_entity": "many2", "id": 2, "many1": [1, 2]}\n',
    ])


@pytest.mark.nodbcleaner
@orm.db_session
def test_dump_to_directory_one_entity(use_testdb, dumpdir):
    pd = PonyDump(testdb)
    _fill_testdb()

    dump_statuses = [
        {'current': 1, 'count': 2, 'pk': (1,), 'entity': 'many1', 'chunk_size': 250},
        {'current': 2, 'count': 2, 'pk': (2,), 'entity': 'many1', 'chunk_size': 250},
        {'current': 2, 'count': 2, 'pk': None, 'entity': 'many1', 'chunk_size': 250},

        {'entity': None, 'path': None, 'current': 0, 'count': 0, 'pk': None},  # Всегда последний
    ]

    filenames = ['many1_dump.jsonl']

    for status in pd.dump_to_directory(dumpdir, entities=['many1']):
        path = status.pop('path')

        if path is not None:
            assert os.path.split(path)[1] in filenames
            assert os.path.isfile(path)
        else:
            status['path'] = path  # Для проверки последнего элемента

        assert status in dump_statuses
        dump_statuses.remove(status)

        if path is None:
            assert not dump_statuses

    assert not dump_statuses


@pytest.mark.nodbcleaner
@orm.db_session
def test_dump_to_directory_exclude_attrs(use_testdb, dumpdir):
    pd = PonyDump(testdb, dict_params={
        'many1': {'exclude': 'many2'},
    })
    _fill_testdb()

    for _ in pd.dump_to_directory(dumpdir):
        pass

    _check_dump_content(dumpdir, 'many1_dump.jsonl', [
        '{"_entity": "many1", "id": 1}\n',
        '{"_entity": "many1", "id": 2}\n',
    ])


# loaddb tests


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_from_files_full(use_testdb, dumpdir):
    os.makedirs(dumpdir)

    with open(os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest1", "k1": 1, "k2": 2, "k3": 3, "test2": 1, "test3": [17]}\n')

    with gzip.open(os.path.join(dumpdir, 'pdtest2_dump.jsonl.gz'), 'wt', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest2", "id": 1, "test1": [1, 2, 3]}\n')

    with open(os.path.join(dumpdir, 'pdtest3_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest3", "foo_bool": true, "foo_datetime": "2017-06-01T01:02:03.999987Z", "foo_float": 0.30000000000000004, "foo_int": -4, "foo_longstr": "longstr", "foo_string": "foo\\u0000😊bar", "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c", "id": 17, "test1": [1, 2, 3]}\n')

    with open(os.path.join(dumpdir, 'many1_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "many1", "id": 1, "many2": [1, 2]}\n')
        fp.write('{"_entity": "many1", "id": 2, "many2": [1, 2]}\n')

    with open(os.path.join(dumpdir, 'many2_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "many2", "id": 1, "many1": [1, 2]}\n')
        fp.write('{"_entity": "many2", "id": 2, "many1": [1, 2]}\n')

    pd = PonyDump(testdb)

    # create test

    load_statuses = [
        {'created': True, 'updated': True, 'entity': 'many1', 'pk': 1, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'many1_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': True, 'updated': True, 'entity': 'many1', 'pk': 2, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many1_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many1_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': True, 'updated': True, 'entity': 'many2', 'pk': 1, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'many2_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': True, 'updated': True, 'entity': 'many2', 'pk': 2, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many2_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many2_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': True, 'updated': True, 'entity': 'pdtest1', 'pk': (1, 2, 3), 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'created': True, 'updated': True, 'entity': 'pdtest3', 'pk': 17, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest3_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest3_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'created': True, 'updated': True, 'entity': 'pdtest2', 'pk': 1, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest2_dump.jsonl.gz'), 'count': 1, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest2_dump.jsonl.gz'), 'count': 1, 'all_count': 7},
        {'path': None, 'entity': None, 'pk': None, 'updated': None, 'created': None, 'count': 7, 'all_count': 7},
    ]

    for statuses in pd.load_from_files([dumpdir]):
        for status in statuses:
            assert status in load_statuses
            load_statuses.remove(status)

    assert not load_statuses
    assert not pd.get_depcache_dict()

    # update test
    PDTest3.select().first().foo_longstr = 'changed string'
    Many2.get(id=2).delete()

    load_statuses = [
        # updated=False, потому что зависимость Many2(2) ещё отсутствует в базе
        {'created': False, 'updated': False, 'entity': 'many1', 'pk': 1, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'many1_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': False, 'updated': False, 'entity': 'many1', 'pk': 2, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many1_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many1_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': False, 'updated': False, 'entity': 'many2', 'pk': 1, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'many2_dump.jsonl'), 'count': 2, 'all_count': 7},
        # ...и создаётся только сейчас
        {'created': True, 'updated': True, 'entity': 'many2', 'pk': 2, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many2_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 2, 'current': 2, 'path': os.path.join(dumpdir, 'many2_dump.jsonl'), 'count': 2, 'all_count': 7},
        {'created': False, 'updated': False, 'entity': 'pdtest1', 'pk': (1, 2, 3), 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'count': 1, 'all_count': 7},
        # Ещё вот тут мы меняли атрибут
        {'created': False, 'updated': True, 'entity': 'pdtest3', 'pk': 17, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest3_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest3_dump.jsonl'), 'count': 1, 'all_count': 7},
        {'created': False, 'updated': False, 'entity': 'pdtest2', 'pk': 1, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest2_dump.jsonl.gz'), 'count': 1, 'all_count': 7},
        {'entity': None, 'updated': None, 'created': None, 'pk': None, 'lineno': 1, 'current': 1, 'path': os.path.join(dumpdir, 'pdtest2_dump.jsonl.gz'), 'count': 1, 'all_count': 7},
        {'path': None, 'entity': None, 'pk': None, 'updated': None, 'created': None, 'count': 7, 'all_count': 7},
    ]

    for statuses in pd.load_from_files([dumpdir]):
        for status in statuses:
            load_statuses.remove(status)
            if status['entity'] == 'many1':
                # Проверяем, что отсутствующая зависимость Many2 положена в depcache
                deps = pd.get_depcache_dict()[(('many1', 'many2'), ('many2', 'many1'))]
                assert (2,) in deps[0].get((status['pk'],))
                assert (status['pk'],) in deps[1].get((2,))

    assert not load_statuses
    assert not pd.get_depcache_dict()

    assert PDTest1.select().count() == 1

    test1 = PDTest1.select().first()
    assert test1.get_pk() == (1, 2, 3)
    assert test1.test2.id == 1
    assert test1.test3.select().count() == 1
    assert test1.test3.select().first().id == 17

    assert PDTest2.select().count() == 1
    test2 = PDTest2.select().first()
    assert test2.get_pk() == 1
    assert test2.test1 is test1  # Pony ORM кэширует всё подряд, поэтому можно is

    assert PDTest3.select().count() == 1
    test3 = PDTest3.select().first()
    assert test3.get_pk() == 17
    assert test3.test1 is test1

    assert test3.foo_bool is True
    assert test3.foo_int == -4
    assert 0.1 + 0.2 == 0.30000000000000004
    assert test3.foo_float == 0.30000000000000004
    assert test3.foo_string == 'foo\u0000😊bar'
    assert test3.foo_longstr == 'longstr'
    assert test3.foo_datetime == datetime(2017, 6, 1, 1, 2, 3, 999987)
    assert test3.foo_uuid == uuid.UUID('8e8cdc11-0785-43a8-8203-66c148c3f57c')

    many1_1, many1_2 = Many1.select().order_by(Many1.id)[:]
    many2_1, many2_2 = Many2.select().order_by(Many2.id)[:]

    assert many1_1.many2.select().order_by(Many2.id)[:] == [many2_1, many2_2]
    assert many1_2.many2.select().order_by(Many2.id)[:] == [many2_1, many2_2]
    assert many2_1.many1.select().order_by(Many1.id)[:] == [many1_1, many1_2]
    assert many2_2.many1.select().order_by(Many1.id)[:] == [many1_1, many1_2]


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_from_files_partial(use_testdb, dumpdir):
    os.makedirs(dumpdir)

    with open(os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest1", "k1": 1, "k2": 2, "k3": 3, "test3": [17]}\n')

    with gzip.open(os.path.join(dumpdir, 'pdtest2_dump.jsonl.gz'), 'wt', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest2", "id": 1, "test1": [1, 2, 3]}\n')

    with open(os.path.join(dumpdir, 'pdtest3_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest3", "foo_bool": true, "foo_datetime": "2017-06-01T01:02:03.999987Z", "foo_float": 0.30000000000000004, "foo_int": -4, "foo_longstr": "longstr", "foo_string": "foo\\u0000😊bar", "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c", "id": 17}\n')

    with open(os.path.join(dumpdir, 'many1_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "many1", "id": 1, "many2": [1, 2]}\n')
        fp.write('{"_entity": "many1", "id": 2}\n')

    with open(os.path.join(dumpdir, 'many2_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "many2", "id": 1, "many1": [1, 2]}\n')
        fp.write('{"_entity": "many2", "id": 2, "many1": [1, 2]}\n')

    pd = PonyDump(testdb)

    for _ in pd.load_from_files([dumpdir]):
        pass

    assert not pd.get_depcache_dict()

    assert PDTest1.select().count() == 1

    test1 = PDTest1.select().first()
    assert test1.get_pk() == (1, 2, 3)
    assert test1.test2.id == 1
    assert test1.test3.select().count() == 1
    assert test1.test3.select().first().id == 17

    assert PDTest2.select().count() == 1
    test2 = PDTest2.select().first()
    assert test2.get_pk() == 1
    assert test2.test1 is test1  # Pony ORM кэширует всё подряд, поэтому можно is

    assert PDTest3.select().count() == 1
    test3 = PDTest3.select().first()
    assert test3.get_pk() == 17
    assert test3.test1 is test1

    many1_1, many1_2 = Many1.select().order_by(Many1.id)[:]
    many2_1, many2_2 = Many2.select().order_by(Many2.id)[:]

    assert many1_1.many2.select().order_by(Many2.id)[:] == [many2_1, many2_2]
    assert many1_2.many2.select().order_by(Many2.id)[:] == [many2_1, many2_2]
    assert many2_1.many1.select().order_by(Many1.id)[:] == [many1_1, many1_2]
    assert many2_2.many1.select().order_by(Many1.id)[:] == [many1_1, many1_2]


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_from_files_notfull(use_testdb, dumpdir):
    os.makedirs(dumpdir)

    with open(os.path.join(dumpdir, 'pdtest1_dump.jsonl'), 'w', encoding='utf-8') as fp:
        fp.write('{"_entity": "pdtest1", "k1": 1, "k2": 2, "k3": 3, "test2": 12, "test3": [17, 19]}\n')

    pd = PonyDump(testdb)

    for _ in pd.load_from_files([dumpdir]):
        pass

    depcache = pd.get_depcache_dict()
    assert depcache

    assert PDTest1.select().count() == 1

    test1 = PDTest1.select().first()
    assert test1.get_pk() == (1, 2, 3)
    assert not test1.test2
    assert test1.test3.select().count() == 0

    assert PDTest2.select().count() == 0
    assert PDTest3.select().count() == 0

    key = (('pdtest1', 'test2'), ('pdtest2', 'test1'))
    assert key in depcache
    assert depcache[key] == [
        {
            (1, 2, 3): {(12,)},
        },
        {
            (12,): {(1, 2, 3)},
        },
    ]

    key = (('pdtest1', 'test3'), ('pdtest3', 'test1'))
    assert key in depcache
    assert depcache[key] == [
        {
            (1, 2, 3): {(19,), (17,)}
        },
        {
            (19,): {(1, 2, 3)},
            (17,): {(1, 2, 3)},
        }
    ]


@pytest.mark.nodbcleaner
@pytest.mark.parametrize('lines', [
    [
        '{"_entity": "many1", "id": 10, "many2": [20]}',
        '{"_entity": "many2", "id": 20}',
    ],
    [
        '{"_entity": "many1", "id": 10}',
        '{"_entity": "many2", "id": 20, "many1": [10]}',
    ],
])
@orm.db_session
def test_load_from_files_relations_all_orders(use_testdb, dumpdir, lines):
    os.makedirs(dumpdir)

    with open(os.path.join(dumpdir, 'some_dump.jsonl'), 'w', encoding='utf-8') as fp:
        for line in lines:
            fp.write(line + '\n')

    pd = PonyDump(testdb)

    for _ in pd.load_from_files([dumpdir]):
        pass

    assert not pd.get_depcache_dict()

    many1 = Many1.select().first()
    many2 = Many2.select().first()

    assert many1.many2.select()[:] == [many2]
    assert many2.many1.select()[:] == [many1]


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_ok_entity_case_insensitive(use_testdb):
    pd = PonyDump(testdb)

    result = pd.json2obj({'_entity': 'mAnY1', 'id': 7, "many2": []})
    assert isinstance(result['obj'], Many1)
    assert result['obj'].id == 7


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_ok_datetime_unix(use_testdb):
    pd = PonyDump(testdb)

    result = pd.json2obj({
        "_entity": "pdtest3",
        "foo_bool": True,
        "foo_float": 0.30000000000000004,
        "foo_int": -4,
        "foo_longstr": "longstr",
        "foo_string": "foo\\u0000😊bar",
        "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c",
        "id": 1,
        "test1": [1, 2, 3],

        "foo_datetime": 3601.999987,
    })

    assert result['obj'].foo_datetime == datetime(1970, 1, 1, 1, 0, 1, 999987)


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_ok_datetime_obj(use_testdb):
    pd = PonyDump(testdb)

    result = pd.json2obj({
        "_entity": "pdtest3",
        "foo_bool": True,
        "foo_float": 0.30000000000000004,
        "foo_int": -4,
        "foo_longstr": "longstr",
        "foo_string": "foo\\u0000😊bar",
        "foo_uuid": "8e8cdc11-0785-43a8-8203-66c148c3f57c",
        "id": 1,
        "test1": [1, 2, 3],

        "foo_datetime": datetime(1970, 1, 1, 2, 0, 3, 999987),
    })

    assert result['obj'].foo_datetime == datetime(1970, 1, 1, 2, 0, 3, 999987)


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_ok_uuid_obj(use_testdb):
    pd = PonyDump(testdb)

    u = uuid.uuid4()

    result = pd.json2obj({
        "_entity": "pdtest3",
        "foo_bool": True,
        "foo_datetime": "2017-06-01T01:02:03.999987Z",
        "foo_float": 0.30000000000000004,
        "foo_int": -4,
        "foo_longstr": "longstr",
        "foo_string": "foo\\u0000😊bar",
        "id": 1,
        "test1": [1, 2, 3],

        "foo_uuid": u,
    })

    assert result['obj'].foo_uuid == u


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_fail_invalid_entity(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        pd.json2obj({'_entity': 'wtfisthat', 'id': 1})

    assert str(excinfo.value) == 'Unknown entity "wtfisthat"'


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_fail_inconsistent_set(use_testdb):
    pd = PonyDump(testdb)

    pd.json2obj({'_entity': 'many1', 'id': 1, 'many2': [2]})

    with pytest.raises(ValueError) as excinfo:
        # many1 не должен быть пуст, так как есть связь
        pd.json2obj({'_entity': 'many2', 'id': 2, 'many1': []})

    assert str(excinfo.value) == 'Inconsistent dump: attribute "many1" of "many2(2,)" conflicts with reverse data'


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_fail_inconsistent_optional_count(use_testdb):
    pd = PonyDump(testdb)

    pd.json2obj({'_entity': 'pdtest4', 'id': 1, 'test1': (1, 2, 3)})
    pd.json2obj({'_entity': 'pdtest4', 'id': 2, 'test1': [1, 2, 3]})

    with pytest.raises(ValueError) as excinfo:
        # test4 — Optional, а на один и тот же PDTest1 один ссылаются аж два PDTest2, так не бывает
        pd.json2obj({'_entity': 'pdtest1', 'k1': 1, 'k2': 2, 'k3': 3})

    assert str(excinfo.value) == 'Inconsistent dump: attribute "test4" of "pdtest1(1, 2, 3)" has multiple values in reverse data'


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_fail_inconsistent_optional_count_2(use_testdb):
    pd = PonyDump(testdb)

    pd.json2obj({'_entity': 'pdtest4', 'id': 1, 'test1': (1, 2, 3)})
    pd.json2obj({'_entity': 'pdtest4', 'id': 2, 'test1': [1, 2, 3]})

    with pytest.raises(ValueError) as excinfo:
        # То же самое, что и в предыдущем тесте, но тут какой-нибудь test4 прописан
        pd.json2obj({'_entity': 'pdtest1', 'k1': 1, 'k2': 2, 'k3': 3, 'test4': 1})

    assert str(excinfo.value) == 'Inconsistent dump: attribute "test4" of "pdtest1(1, 2, 3)" has multiple values in reverse data'


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_fail_inconsistent_optional_value(use_testdb):
    pd = PonyDump(testdb)

    pd.json2obj({'_entity': 'pdtest4', 'id': 1, 'test1': (1, 2, 3)})

    with pytest.raises(ValueError) as excinfo:
        # test4 ссылается не на тот PDTest4, который прописан в дампе самого PDTest4
        pd.json2obj({'_entity': 'pdtest1', 'k1': 1, 'k2': 2, 'k3': 3, 'test4': 7})

    assert str(excinfo.value) == 'Inconsistent dump: attribute "test4" of "pdtest1(1, 2, 3)" conflicts with reverse data'


@pytest.mark.nodbcleaner
@orm.db_session
def test_json2obj_fail_unknown_attr(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        # test4 ссылается не на тот PDTest4, который прописан в дампе самого PDTest4
        pd.json2obj({'_entity': 'pdtest4', 'id': 1, 'wtfisthat': 'that', 'andthat': 'that'})

    x = 'Unknown attributes in dump of model "pdtest4": '
    assert str(excinfo.value) in (x + 'wtfisthat, andthat', x + 'andthat, wtfisthat')


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_entities_fail_invalid_json_syntax(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        for _ in pd.load_entities(io.StringIO('}')):
            pass

    assert str(excinfo.value).startswith('Invalid JSON on line 1: ')


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_entities_fail_invalid_json_no_entity(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        for _ in pd.load_entities(io.StringIO('{}')):
            pass

    assert str(excinfo.value) =='Invalid dump format on line 1'


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_entities_fail_invalid_json_nonstr_entity(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        for _ in pd.load_entities(io.StringIO('{"_entity": 7}')):
            pass

    assert str(excinfo.value) =='Invalid dump format on line 1'


@pytest.mark.nodbcleaner
@orm.db_session
def test_load_entities_fail_invalid_json_unknown_entity(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        for _ in pd.load_entities(io.StringIO('{"_entity": "wat"}')):
            pass

    assert str(excinfo.value) =='Unknown entity "wat" on line 1'


@pytest.mark.nodbcleaner
@orm.db_session
def test_get_entities_dict_from_db(use_testdb):
    result = ponydump.get_entities_dict(testdb)

    assert result == {
        'pdtest1': PDTest1,
        'pdtest2': PDTest2,
        'pdtest3': PDTest3,
        'pdtest4': PDTest4,
        'many1': Many1,
        'many2': Many2,
    }


@pytest.mark.nodbcleaner
@orm.db_session
def test_get_entities_from_list(use_testdb):
    result = ponydump.get_entities_dict([PDTest2, Many1])

    assert result == {
        'pdtest2': PDTest2,
        'many1': Many1,
    }


@pytest.mark.nodbcleaner
@orm.db_session
def test_depmap_ok(use_testdb):
    pd = PonyDump(testdb)

    # Строго говоря, порядок не абсолютно определён, и некоторые не-required
    # зависимости позволяют менять модели местами, но у обязательных
    # зависимостей строгий порядок: нельзя зависеть от моделей ниже по списку
    assert pd.depmap == [
        # (entity_name, ({required}, {optional}, {set}))
        ('many1', ({}, {}, {'many2': 'many2'})),
        ('many2', ({}, {}, {'many1': 'many1'})),
        ('pdtest1', ({}, {'test2': 'pdtest2', 'test4': 'pdtest4'}, {'test3': 'pdtest3'})),
        ('pdtest3', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest4', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest2', ({'test1': 'pdtest1'}, {}, {})),
    ]


@pytest.mark.nodbcleaner
@orm.db_session
def test_put_depmap_entity_after_ok(use_testdb):
    pd = PonyDump(testdb)

    pd.put_depmap_entity_after('many1', 'pdtest3')
    assert pd.depmap == [
        ('many2', ({}, {}, {'many1': 'many1'})),
        ('pdtest1', ({}, {'test2': 'pdtest2', 'test4': 'pdtest4'}, {'test3': 'pdtest3'})),
        ('pdtest3', ({}, {'test1': 'pdtest1'}, {})),
        ('many1', ({}, {}, {'many2': 'many2'})),
        ('pdtest4', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest2', ({'test1': 'pdtest1'}, {}, {})),
    ]


@pytest.mark.nodbcleaner
@orm.db_session
def test_put_depmap_entity_after_all_ok(use_testdb):
    pd = PonyDump(testdb)

    pd.put_depmap_entity_after('many1', after_entity=None)
    assert pd.depmap == [
        ('many2', ({}, {}, {'many1': 'many1'})),
        ('pdtest1', ({}, {'test2': 'pdtest2', 'test4': 'pdtest4'}, {'test3': 'pdtest3'})),
        ('pdtest3', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest4', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest2', ({'test1': 'pdtest1'}, {}, {})),
        ('many1', ({}, {}, {'many2': 'many2'})),
    ]


@pytest.mark.nodbcleaner
@orm.db_session
def test_put_depmap_entity_after_required_fail(use_testdb):
    pd = PonyDump(testdb)

    with pytest.raises(ValueError) as excinfo:
        pd.put_depmap_entity_after('pdtest1', after_entity='pdtest2')

    assert str(excinfo.value) == 'Required dependencies does not allow this moving'

    assert pd.depmap == [
        ('many1', ({}, {}, {'many2': 'many2'})),
        ('many2', ({}, {}, {'many1': 'many1'})),
        ('pdtest1', ({}, {'test2': 'pdtest2', 'test4': 'pdtest4'}, {'test3': 'pdtest3'})),
        ('pdtest3', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest4', ({}, {'test1': 'pdtest1'}, {})),
        ('pdtest2', ({'test1': 'pdtest1'}, {}, {})),
    ]
