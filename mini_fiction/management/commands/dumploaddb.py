#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import uuid
from datetime import datetime

from pony import orm

from mini_fiction.database import db


dumpdb_params = {
    'story': {'exclude': (
        'edit_log', 'story_views_set', 'votes', 'favorites', 'bookmarks',
        'comments', 'activity',
    )},
    'author': {'exclude': (
        'activity', 'edit_log',
        'favorites', 'bookmarks', 'contributing', 'coauthorseries',
        'news', 'votes', 'views',
        'news_comments', 'news_comment_edits', 'news_comment_votes',
        'story_comments', 'story_comment_edits', 'story_comment_votes',
    )},
    'storycomment': {'exclude': (
        'answers', 'edits', 'votes',
    )},
    'newscomment': {'exclude': (
        'answers', 'edits', 'votes',
    )},
    'category': {'exclude': (
        'stories',
    )},
    'character': {'exclude': (
        'stories',
    )},
    'classifier': {'exclude': (
        'stories',
    )},
}


restoredb_order = (
    'author',

    'charactergroup',
    'character',
    'category',
    'classifier',
    'rating',

    'story',
    'chapter',
    'storycontributor',
    'storycomment',

    'series',
    'inseriespermissions',
    'coauthorsseries',

    'newsitem',
    'newsitemcomment',
)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(self, o)


def dumpdb_entity(path, name, entity):
    # TODO: custom primary key
    min_id = orm.select(orm.min(x.id) for x in entity).first()
    count = orm.select(x.id for x in entity).count()
    step = 50
    if min_id is None:
        print(path, 'is empty')
        return

    dict_params = dumpdb_params.get(name)

    print(path)
    je = JSONEncoder(ensure_ascii=False, sort_keys=True)
    with open(path, 'w', encoding='utf-8') as fp:
        fp.write('dump:' + name + '\n')

        begin = min_id
        ok_count = 0
        while True:
            items = orm.select(x for x in entity if x.id >= begin).order_by(entity.id)[:50]
            ok_count += len(items)
            sys.stdout.write(' {}/{}\r'.format(ok_count, count))
            sys.stdout.flush()
            if not items:
                break
            for item in items:
                dumpdb_entity_iter(fp, item, je, params=dict_params)
            begin = items[-1].id + 1
        print()


def dumpdb_entity_iter(fp, item, je, params=None):
    dict_params = {'with_lazy': True, 'with_collections': True}
    if params:
        dict_params.update(params)
    jsondata = je.encode(item.to_dict(**dict_params))
    fp.write('\n' + jsondata + '\n')


def dumpdb(dirpath, model_names):
    table = {x.lower(): db.entities[x] for x in db.entities}
    if 'all' in model_names:
        model_names = list(sorted(table))
    print(dirpath, model_names)
    for x in model_names:
        if x not in table:
            raise ValueError('Unknown model: {}'.format(x))

    if not os.path.isdir(dirpath):
        os.mkdir(dirpath)

    for x in model_names:
        dumpdb_entity(os.path.join(dirpath, x + '_dump.json.txt'), x, table[x])


def loaddb_entity(data, entity, restore_queue):
    create_data = {}
    create_relations = {}
    create_collections = {}
    create_new_relations = {}
    create_new_collections = {}

    edit = False
    if data.get('id') is not None:
        obj = entity.get(id=data['id'])
        edit = obj is not None

    for name, value in data.items():
        field = getattr(entity, name)
        assert isinstance(field, orm.core.Attribute)

        if issubclass(field.py_type, db.Entity):
            # Отношения могут быть ещё не загружены в БД
            relation_name = field.py_type.__name__.lower()
            if value is not None and isinstance(value, dict):
                # Если в значении не id, а словарь, то файлик нам предлагает это отношение создать
                # (dumpdb такое не генерирует; просто удобно при ручном заполнении)
                assert not isinstance(field, orm.core.Collection)
                if edit and value.get('id') is None:
                    raise ValueError('Cannot create relation without primary key because it is dangerous')
                rel = field.py_type.get(id=value['id']) if value.get('id') is not None else None
                if rel is not None:
                    # Существующий атрибут пересоздавать не будем
                    create_relations[name] = rel
                elif isinstance(field, orm.core.Required):
                    # Обязательный атрибут придётся создать сразу
                    rel = field.py_type(**value)
                    rel.flush()
                    create_relations[name] = rel
                else:
                    # Опциональный отложим
                    create_new_relations[name] = value

            elif value is not None and isinstance(value, list) and set(isinstance(x, dict) for x in value) == {True}:
                # То же самое, но для коллекций
                assert isinstance(field, orm.core.Collection)
                items = []
                for item in value:
                    if edit and item.get('id') is None:
                        raise ValueError('Cannot create relation without primary key because it is dangerous')
                    rel = field.py_type.get(id=item['id']) if item.get('id') is not None else None
                    items.append(rel or item)
                create_new_collections[name] = items

            elif value is None or relation_name in restore_queue:
                # Если отношение пустое, то и делать ничего не надо
                # Если отношение в очереди на потом, то просто не создаём связь
                # (надеемся, что у этого самого отношения связь тоже прописана)
                assert not isinstance(field, orm.core.Required)
                if isinstance(field, orm.core.Collection):
                    create_collections[name] = []
                else:
                    create_relations[name] = None

            else:
                # Если в очереди нету, то запрашиваем из БД
                if isinstance(field, orm.core.Collection):
                    # TODO: custom primary key
                    relations = field.py_type.select(lambda x: x.id in value)[:]  # pylint: disable=W0640
                    if len(relations) != len(value):
                        raise ValueError('Relation items {} ({}) for {} not found'.format(name, relation_name, entity.__name__))
                    create_collections[name] = relations
                else:
                    # TODO: custom primary key
                    relation = field.py_type.select(lambda x: x.id == value).first()  # pylint: disable=W0640
                    if relation is None:
                        raise ValueError('Relation {} ({}) for {} not found'.format(name, relation_name, entity.__name__))
                    create_relations[name] = relation

        else:
            # С примитивами ничего особенного делать не надо, только дату распарсить
            if value is not None and field.py_type is datetime:
                create_data[name] = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                create_data[name] = value

    kwargs = dict(create_data)
    kwargs.update(create_relations)  # Уже существующие отношения (в т.ч. созданные выше обязательные)
    if not edit:
        obj = entity(**kwargs)
        obj.flush()  # Получаем первичный ключ
    else:
        for name, value in kwargs.items():
            setattr(obj, name, value)

    # Уже существующие отношения в коллекциях
    for name, items in create_collections.items():
        ids = [x.id for x in getattr(obj, name)]
        for rel in items:
            if not edit or rel.id not in ids:
                getattr(obj, name).add(rel)

    # Создаваемые опциональные отношения
    for name, objkeys in create_new_relations.items():
        assert not edit or objkeys.get('id') is not None
        field = getattr(obj, name)
        objkeys[field.reverse.name] = obj
        rel = field.py_type(**objkeys)
        rel.flush()

    # Создаваемые опциональные отношения в коллекциях
    for name, items in create_new_collections.items():
        for objkeys in items:
            assert not edit or objkeys.get('id') is not None
            getattr(obj, name).create(**objkeys)

    if not edit:
        print('Created {} {}'.format(entity.__name__, obj.id))
    else:
        print('Updated {} {}'.format(entity.__name__, obj.id))


def loaddb(pathlist, force=False):
    files = []
    for x in pathlist:
        if os.path.isdir(x):
            files.extend(os.path.join(x, f) for f in os.listdir(x))
        elif os.path.isfile(x):
            files.append(x)
        else:
            raise OSError('Cannot parse path {}'.format(x))

    table = {x.lower(): db.entities[x] for x in db.entities}
    files_by_model = {x: [] for x in table}

    # check
    for f in files:
        with open(f, 'r', encoding='utf-8-sig') as fp:
            data = fp.readline()
            newline = fp.read(1)
        if data[:5] != 'dump:' or data[5:-1] not in files_by_model or newline != '\n':
            raise ValueError('Invalid file {}'.format(f))
        files_by_model[data[5:-1]].append(f)

    restore_queue = [x for x in restoredb_order if files_by_model.get(x)]
    restore_queue.extend(sorted([x for x in files_by_model if files_by_model.get(x) and x not in restore_queue]))

    # check
    notempty = []
    for name in restore_queue:
        entity = table[name]
        if entity.select().exists():
            notempty.append(name)

    if notempty:
        print('Some entities are not empty:')
        for x in notempty:
            print(' -{} (table {})'.format(x, table[x]._table_))
        if not force:
            print('Please delete it with relations before loaddb.')
            orm.rollback()
            return
        if input('Continue? y/n ') not in ('Y', 'y'):
            orm.rollback()
            return

    while restore_queue:
        name = restore_queue.pop(0)
        entity = table[name]
        for f in files_by_model[name]:
            print('Load {} from {}...'.format(name, f))
            with open(f, 'r', encoding='utf-8-sig') as fp:
                line = fp.readline()
                assert line == 'dump:{}\n'.format(name)
                line = fp.readline()
                assert line == '\n'

                cache = ''
                while True:
                    line = fp.readline()
                    if not line and not cache:
                        break
                    if line and line != '\n':
                        cache += line
                        continue
                    loaddb_entity(json.loads(cache), entity, restore_queue)
                    cache = ''
                    if not line:
                        break
                orm.commit()

    print('Finished.')
