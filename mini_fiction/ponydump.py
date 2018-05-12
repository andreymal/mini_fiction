#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=W0212,W0640

import os
import gzip
import json
import uuid
from datetime import datetime

from pony import orm


class JSONEncoder(json.JSONEncoder):
    def default(self, o):  # pragma: no cover
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)


class PonyDump(object):
    def __init__(self, database, dict_params=None, chunk_sizes=None, default_chunk_size=250):
        '''Дампилка указанной базы данных.

        :param Database database: база данных Pony ORM
        :param dict dict_params: дополнительные параметры, которые будут
          скормлены в вызов ``entity.to_dict()``. Ключи — названия моделей
          в lowercase, значения — собственно параметры (словарь)
        '''

        self.db = database
        self.dict_params = dict(dict_params or {})
        self.chunk_sizes = dict(chunk_sizes or {})
        self.default_chunk_size = default_chunk_size

        self.entities = get_entities_dict(self.db)  # {name: Entity}
        # Формат элемента depmap: [имя модели, (
        #     {имя Required атрибута: имя модели-зависимости},
        #     {имя Optional атрибута: имя модели-зависимости},
        #     {имя Set атрибута: имя модели-зависимости},
        # )]
        self.depmap = self._build_depmap()
        self.depsdict = dict(self.depmap)
        self.je = JSONEncoder(ensure_ascii=False, sort_keys=True)

        # Кэш для первичных ключей из нескольких атрибутов; используется для
        # преобразования ключа из вида ``(1, 2)`` в ``{'pk1': 1, 'pk2': 2}``
        self.pkmap = {name: [x.name for x in e._pk_attrs_] for name, e in self.entities.items()}

        # Список всех-всех атрибутов для каждой модели
        self.attr_names = {
            name: set(x.name for x in e._get_attrs_(with_collections=True, with_lazy=True))
            for name, e in self.entities.items()
        }

        # Это кэш опциональных зависимостей. Когда у загруженного объекта
        # ещё не загружены зависимости в БД, сюда кладутся ожидаемые
        # первичные ключи, чтобы проставить зависимости позже, когда
        # объекты появятся.
        # Формат:
        # - ключи: (('модель1', 'атрибут1'), ('модель2', 'атрибут2'))
        # - значения — два зеркальных словаря, дублирующих друг друга ради
        #   производительности: [{ключмодели1: {ключмодели2, ключмодели3}},
        #   {ключмодели2: {ключмодели1}, ключмодели3: {ключмодели1}}]
        self._depcache = {}

    def _build_depmap(self):
        '''Строит список зависимостей моделей Pony ORM друг от друга.
        Каждая модель в списке имеет обязательные зависимости только
        от моделей, стоящих выше. Сортировка опциональных зависимостей
        не определена.
        '''

        # Формируем из моделей словарь имя:модель
        entities = self.entities
        if not entities:  # pragma: no cover
            return []

        # Для начала просто построим словарь имя:список_зависимостей и дальше уже
        # будем работать с ним. Первый dict — Required, второй — Optional,
        # третий — Set.
        # В ключах названия атрибутов, в значениях названия моделей (ибо не всегда
        # совпадают)
        depsdict = {k: ({}, {}, {}) for k in entities}

        for name, entity in entities.items():
            for attr in entity._get_attrs_(with_collections=True, with_lazy=True):
                if not isinstance(attr, (orm.core.Required, orm.core.Optional, orm.core.Set)):  # pragma: no cover
                    continue
                if not isinstance(attr.py_type, orm.core.EntityMeta):
                    continue

                # Ищем модель, от которой зависим
                dep = None
                depname = None
                for k, v in entities.items():
                    if v is attr.py_type:
                        dep = v
                        depname = k
                        break
                assert dep is not None and depname

                # Запоминаем эту модель как обязательную или опциональную зависимость
                if isinstance(attr, orm.core.Required):
                    depsdict[name][0][attr.name] = depname
                elif isinstance(attr, orm.core.Optional):
                    depsdict[name][1][attr.name] = depname
                else:
                    depsdict[name][2][attr.name] = depname

        # А теперь разворачиваем наш словарь в упорядоченный список: в несколько
        # итераций проходимся по словарю и переносим в список модели, зависимости
        # которых уже есть в списке, и так до тех пор, пока словарь не опустошится
        deps = []

        # Для красоты сперва учитываем и обязательные, и опциональные зависимости,
        # а когда не сможем их разрулить (например, циклическая зависимость или
        # зависимость модели от самой себя), переключаемся на учёт только
        # обязательных
        with_optdeps = 2

        while depsdict:
            tomove = []

            # Перебираем модели в словаре
            for name, entitydeps in depsdict.items():
                # Смотрим, остались ли неперенесённые зависимости
                ok = True

                if with_optdeps == 2:
                    entitydeps = set(entitydeps[0].values()) | set(entitydeps[1].values()) | set(entitydeps[2].values())
                elif with_optdeps == 1:
                    entitydeps = set(entitydeps[0].values()) | set(entitydeps[1].values())
                else:
                    entitydeps = set(entitydeps[0].values())

                for dep in entitydeps:
                    if dep in depsdict:
                        ok = False
                        break
                if ok:
                    # Если не остались, то переносим эту модель
                    tomove.append(name)

            if not tomove:
                if with_optdeps:
                    with_optdeps -= 1
                    continue
                else:  # pragma: no cover
                    raise ValueError('Cannot resolve dependencies for {}'.format(', '.join(depsdict)))

            tomove.sort()

            for name in tomove:
                depinfo = depsdict.pop(name)
                deps.append((name, depinfo))

        return deps

    def put_depmap_entity_after(self, entity, after_entity=None):
        '''В методе _build_depmap() сортировка моделей по опциональным
        зависимостям не определена, однако некоторые перестановки могут сильно
        улучшить производительность. Этот метод позволяет поставить
        одну модель после другой модели в списке зависимостей, что в некоторых
        случаях сильно снижает нагрузку на кэш зависимостей. Метод выполняет
        проверку обязательных зависимостей и накосячить не даст.
        '''

        entity_pos = [x[0] for x in self.depmap].index(entity)

        if after_entity:
            after_pos = [x[0] for x in self.depmap].index(after_entity)
            if entity_pos >= after_pos:
                return

            # Перемещаем
            new_depmap = self.depmap[:]
            new_depmap.insert(after_pos + 1, new_depmap[entity_pos])
            a = new_depmap.pop(entity_pos)

            # Внутренние проверки
            assert a[0] == entity
            assert a is new_depmap[after_pos]

        else:
            # При after_entity=None просто пихаем в конец
            if self.depmap[-1][0] == entity:
                return
            new_depmap = self.depmap[:]
            a = new_depmap.pop(entity_pos)
            assert a[0] == entity
            new_depmap.append(a)
            after_pos = len(new_depmap) - 1

        # Проверяем обязательные зависимости: проходимся ко каждой модели
        # перед перемещённой и смотрим, что всё в порядке
        deps = [x[0] for x in new_depmap[:after_pos]]
        for i in range(after_pos):  # i - порядковый номер модели в depmap
            # Проходимся по обязательным зависимостям i-й модели
            for dep_name in new_depmap[i][1][0].values():
                # Если среди (0..i-1) моделей нужной нет, то всё плохо
                if dep_name not in deps[:i]:
                    raise ValueError('Required dependencies does not allow this moving')

        # После всех проверок применяем изменения
        self.depmap = new_depmap

    def get_entity_name(self, entity):
        name = None
        for k, v in self.entities.items():
            if v is entity or isinstance(entity, v):
                name = k
                break
        if not name:
            raise TypeError('Unknown entity: {}'.format(entity))
        return name

    def get_depcache_dict(self):
        return self._depcache

    def dc_get_all(self, name, attr=None, pk=None):
        '''Возвращает словарь: в ключах — атрибуты указанной модели,
        в значениях — первичные ключи указанных зависимостей (тип всегда set,
        даже для Optional). Если кэш пуст, вернётся пустой словарь (даже при
        указанном attr).

        :param str name: название модели, lowercase
        :param str attr: если указано, вернётся словарь только с этим
          атрибутом
        :param tuple pk: если указано, будут добавлены только те зависимости,
          которые происанны для указанного первичного ключа модели name
        '''

        if pk is not None:
            if not isinstance(pk, tuple):
                raise TypeError('pk must be tuple')

        result = {}

        d = self._depcache

        for key in d:
            # Отбираем только нашу модель из кэша
            if key[0][0] != name and key[1][0] != name:
                continue

            # Выясняем, о каком Optional/Set атрибуте речь в данном случае
            if key[0][0] == name:
                cur_attr = key[0][1]
            else:
                cur_attr = key[1][1]

            # Если с нас спрашивают конкретный атрибут и сейчас не он,
            # то едем дальше
            if attr and attr != cur_attr:
                continue
            assert cur_attr not in result

            # deps — словарик первичных ключей с зависимостями вида
            # {объект1: {зависимость1, зависимость2, ...}, ...}
            if key[0][0] == name:
                deps = d[key][0]  # если в depcache лежит прямой порядок
            else:
                deps = d[key][1]  # если в depcache лежит обратный порядок

            # Собираем нужные нам значения из словарика
            if pk:
                if pk in deps:
                    result[cur_attr] = set((pk, x) for x in deps[pk])
            else:
                result[cur_attr] = set()
                for xpk in deps:
                    result[cur_attr] |= set((xpk, x) for x in deps[xpk])

        return result

    def dc_put(self, name, attr, pk, dep_pk):
        '''Добавляет в кэш ожидаемую опциональную (Optional или Set)
        зависимость.

        :param str name: название модели в lowercase
        :param str attr: название атрибута с опциональной зависимостью
        :param tuple pk: первичный ключ модели
        :param tuple dep_pk: первичный ключ ожидаемой опциональной зависимости
        '''

        d = self._depcache

        assert isinstance(pk, tuple)
        assert isinstance(dep_pk, tuple)

        entity = self.entities[name]
        attr_obj = getattr(entity, attr)

        depname = self.get_entity_name(attr_obj.py_type)
        depattr = attr_obj.reverse.name

        key = [(name, attr), (depname, depattr)]
        key.sort()
        key = tuple(key)

        if key[0][0] == name:
            value = (pk, dep_pk)
        else:
            value = (dep_pk, pk)

        if key not in d:
            # Дублирование ради производительности:
            # В первом словаре связь модель1→модель2,
            # во втором модель2→модель1
            d[key] = [{}, {}]

        # У Set атрибутов есть несколько зависимых объектов,
        # поэтому set и здесь
        if value[0] not in d[key][0]:
            d[key][0][value[0]] = set()
        d[key][0][value[0]].add(value[1])

        # Зеркальное дублирование для производительности
        if value[1] not in d[key][1]:
            d[key][1][value[1]] = set()
        d[key][1][value[1]].add(value[0])

    def dc_delete(self, name, attr, pk, dep_pk):
        '''Удаляет из кэша ожидаемую опциональную (Optional или Set)
        зависимость.

        :param str name: название модели в lowercase
        :param str attr: название атрибута с опциональной зависимостью
        :param tuple pk: первичный ключ модели
        :param tuple dep_pk: первичный ключ ожидаемой опциональной зависимости
        '''

        d = self._depcache

        assert isinstance(pk, tuple)
        assert isinstance(dep_pk, tuple)

        entity = self.entities[name]
        attr_obj = getattr(entity, attr)

        depname = self.get_entity_name(attr_obj.py_type)
        depattr = attr_obj.reverse.name

        key = [(name, attr), (depname, depattr)]
        key.sort()
        key = tuple(key)

        if key[0][0] == name:
            value = (pk, dep_pk)
        else:
            value = (dep_pk, pk)

        if key in d:
            if value[0] in d[key][0]:
                deps_for_pk = d[key][0][value[0]]
                if value[1] in deps_for_pk:
                    deps_for_pk.remove(value[1])
                if not deps_for_pk:
                    d[key][0].pop(value[0])

            if value[1] in d[key][1]:
                deps_for_pk = d[key][1][value[1]]
                if value[0] in deps_for_pk:
                    deps_for_pk.remove(value[0])
                if not deps_for_pk:
                    d[key][1].pop(value[1])

            if not d[key][0] and not d[key][1]:
                del d[key]

    # Методы для дампа базы данных

    def obj2json(self, obj, name=None):
        '''Дампит указанный объект базы данных в формат, совместимый с JSON.

        :param Entity obj: объект из базы данных
        :param str name: название модели объекта в lowercase, рекомендуется
          указать для большей производительности
        :rtype: dict
        '''

        if not name:
            name = self.get_entity_name(obj)

        dict_params = {'with_lazy': True, 'with_collections': True}
        if name in self.dict_params:
            dict_params.update(self.dict_params[name])
        result = obj.to_dict(**dict_params)
        assert '_entity' not in result
        result['_entity'] = name
        return result

    def dump_entity(self, entity, fp, chunk_size=250, binary_mode=False, sanitizer=None):
        '''Дампит указанную модель в указанный вывод в формате JSON Lines.
        Генератор, yield'ит прогресс. Если yield'ится 'pk': None, значит всё.

        :param entity: название модели в lowercase или сама модель
        :param file fp: файлоподобный объект, имеющий метод write, в который
          можно скармливать строки
        :param int chunk_size: по сколько штук за раз брать объектов из базы
        :param bool binary_mode: указывает, в каком режиме открыт
          файлоподобный объект: текстовом (False) или бинарном (True)
        :param sanitizer: функция, которой будет передан список словарей
          дампа перед его записью; можно его изменять
        '''

        if isinstance(entity, str):
            name = entity
            entity = self.entities[name]
        else:
            name = self.get_entity_name(entity)

        # LongStr по умолчанию имеет lazy=True, и во избежание N+1 запроса
        # указываем, что их грузить надо тоже
        lazy_attrs = []
        for attr in entity._get_attrs_(with_collections=False, with_lazy=True):
            if getattr(attr, 'lazy'):
                lazy_attrs.append(attr)

        # Модели теоретически могут иметь первичный ключ из нескольких
        # атрибутов, учитываем это. Для наглядности дальше в комментариях
        # используется первичный ключ (foo, bar, baz)
        pk_attrs_objs = list(entity._pk_attrs_)
        pk_attrs = self.pkmap[name]
        assert pk_attrs == [x.name for x in pk_attrs_objs]

        # Сортируем по первичному ключу. Берём самый «маленький» объект
        # из базы и дальше от него забираем по chunk_size объектов
        with orm.db_session:
            current_count = 0
            count = entity.select().count()
            pk = entity.select().order_by(*pk_attrs_objs).first()
            if pk is not None:
                pk = pk.get_pk()  # кортеж из значений атрибутов первичного ключа
                if not isinstance(pk, tuple):
                    pk = (pk,)

        assert not pk or len(pk_attrs) == len(pk)

        yield {'current': min(count, 1), 'count': count, 'pk': pk}
        if not pk:
            return

        first = True
        while pk:
            with orm.db_session:
                # Тут ультра сложна: селектим объекты, прописывая в условии
                # where корректную сортировку (просто x.get_pk() > pk никто
                # не даст, если len(pk) > 1)

                objs = None
                pk_zip = list(zip(pk_attrs, pk))

                while pk_zip:
                    # WHERE foo == 1 AND bar == 2 AND baz > 3

                    # Поня имеет баг https://github.com/ponyorm/pony/issues/223
                    # eval() обходит этот баг, после фикса можно его убрать
                    # (а ещё из-за этого течёт память, что хорошо заметно при
                    # chunk_size=1)

                    q = entity.select()
                    if len(pk) == 1 and pk_zip[0][0] == 'id':
                        # Отдельно выписан частный и самый частый случай, чтоб eval память кушал поменьше
                        value = pk_zip[0][1]
                        if not first:
                            q = q.filter(lambda x: x.id > value)
                        else:
                            q = q.filter(lambda x: x.id >= value)
                    else:
                        for attr, value in pk_zip[:-1]:  # pylint: disable=unused-variable
                            # Если что, с замыканием проблем нет, поня лямбду вообще не запускает
                            q = q.filter(eval('lambda x: getattr(x, attr) == value'))  # pylint: disable=W0123
                        attr, value = pk_zip[-1]
                        if not first:
                            q = q.filter(eval('lambda x: getattr(x, attr) > value'))  # pylint: disable=W0123
                        else:
                            q = q.filter(eval('lambda x: getattr(x, attr) >= value'))  # pylint: disable=W0123

                    if lazy_attrs:
                        q = q.prefetch(*lazy_attrs)

                    objs = q[:chunk_size]
                    first = False
                    if objs:
                        # Если объекты есть, то всё
                        break

                    # Если объектов с текущими pk не осталось, то выкидываем
                    # меньший атрибут и пытаемся foo == 1 AND bar > 2
                    # и так в цикле пока всё не кончится
                    pk_zip = pk_zip[:-1]

                if not objs:
                    assert not pk_zip
                    pk = None
                    break

                # Если объекты из базы достались, то дампим их
                dump = [self.obj2json(x, name) for x in objs]
                pk = objs[-1].get_pk()
                if not isinstance(pk, tuple):
                    pk = (pk,)
                del q, objs, pk_zip

                if sanitizer:
                    sanitizer(dump)

            if dump:  # sanitizer мог почистить
                x = '\n'.join(self.je.encode(x) for x in dump)
                fp.write(x.encode('utf-8') if binary_mode else x)
                fp.write(b'\n' if binary_mode else '\n')
                current_count += len(dump)
            dump = None
            yield {'current': current_count, 'count': count, 'pk': pk}

        yield {'current': current_count, 'count': count, 'pk': None}

    def dump_to_directory(self, path, entities=None, chunk_sizes=None, gzip_compression=0):
        '''Дампит базу данных в указанный каталог. Если не указаны модели,
        дампит все. Генератор, yield'ит процесс. Если yield'ится 'pk': None,
        значит закончили с текущей моделью, если 'entity': None, значит
        закончили совсем.

        :param str path: путь к каталогу, в который дампить
        :param list entites: список моделей для дампа (если пусто, то все),
          строки в lowercase
        :param dict chunk_sizes: по сколько штук за раз брать объектов из базы
        :param int gzip_compression: если больше нуля, файлы дампа будут сжаты
          с указанной степенью сжатия (1-9) и сохранены с расширением jsonl.gz
        '''

        chunk_sizes1 = dict(self.chunk_sizes)
        if chunk_sizes:
            chunk_sizes1.update(chunk_sizes)
        chunk_sizes = chunk_sizes1
        del chunk_sizes1

        if entities:
            entities = set(entities)
            l = len(entities)
            # Одновременно проверка правильности имён и сортировка по зависимостям
            entities = [x[0] for x in self.depmap if x[0] in entities]
            if len(entities) != l:
                raise ValueError('Some entities not found')
        else:
            entities = [x[0] for x in self.depmap]

        path = os.path.abspath(path)
        if not os.path.isdir(path):
            os.makedirs(path)

        for entity in entities:
            file_path = os.path.join(path, '{}_dump.jsonl'.format(entity))
            if gzip_compression > 0:
                file_path += '.gz'
                fp = gzip.open(file_path, 'wt', encoding='utf-8')
            else:
                fp = open(file_path, 'w', encoding='utf-8')

            with fp:
                chunk_size = max(1, chunk_sizes.get(entity, self.default_chunk_size))
                for progress in self.dump_entity(entity, fp, chunk_size=chunk_size):
                    progress['entity'] = entity
                    progress['path'] = file_path
                    progress['chunk_size'] = chunk_size
                    yield progress

        yield {'entity': None, 'path': None, 'current': 0, 'count': 0, 'pk': None}

    # Методы для загрузки базы данных из дампа

    def _prepare_deps_from_depcache(self, name, entity, pk, dump):
        # На объект, в данный момент загружаемый из дампа, могли ссылаться
        # ранее загружаемые объекты как на опциональную зависимость; так как
        # объект мы уже создаём, то чистим кэш от этих прописанных
        # зависимостей и забираем их из базы

        result = {}

        for depattr, depdata in self.dc_get_all(name, pk=pk).items():
            assert depdata

            if depattr in dump:
                # Если эта связь уже прописана в текущем дампе, то просто
                # проверяем на непротиворечивость и отдаём на обработку
                # в другие _prepare* методы

                # (переводим ключи из depcache в формат (1,) → 1 для сравнения с дампом)
                dep_pks = set((x[1][0] if len(x[1]) == 1 else x[1]) for x in depdata)

                if isinstance(getattr(entity, depattr), orm.core.Set):
                    s_dump = set(dump[depattr])
                    if dep_pks & s_dump != dep_pks:  # дамп должен содержать в себе как минимум всё из depcache
                        raise ValueError('Inconsistent dump: attribute "{}" of "{}{}" conflicts with reverse data'.format(depattr, name, pk))
                else:
                    if len(depdata) != 1:
                        raise ValueError('Inconsistent dump: attribute "{}" of "{}{}" has multiple values in reverse data'.format(depattr, name, pk))
                    k_dump = tuple(dump[depattr]) if isinstance(dump[depattr], list) else dump[depattr]
                    if k_dump != tuple(dep_pks)[0]:
                        raise ValueError('Inconsistent dump: attribute "{}" of "{}{}" conflicts with reverse data'.format(depattr, name, pk))

                # Никаких del dump[depattr] не делаем
                continue

            depname = self.get_entity_name(getattr(entity, depattr).py_type)
            objs = []

            # TODO: как-нибудь одним select'ом? (вообще это всё довольно тормознуто)

            for _pk, dep_pk in depdata:
                assert _pk == pk

                dep_pk_dict = dict(zip(self.pkmap[depname], dep_pk))
                obj = self.entities[depname].get(**dep_pk_dict)
                assert obj is not None, 'looks like depcache is broken, it is a bug'
                objs.append(obj)
                self.dc_delete(name, depattr, pk, dep_pk)

            if isinstance(getattr(entity, depattr), orm.core.Set):
                result[depattr] = objs
            else:
                if len(objs) > 1:
                    raise ValueError('Inconsistent dump: attribute "{}" of "{}{}" has multiple values in reverse data'.format(depattr, name, pk))
                result[depattr] = objs[0] if objs else None

        return result

    def _prepare_required_deps(self, name, entity, pk, dump):
        '''Этот метод достаёт из базы все обязательные зависимости, пользуясь
        информацией из дампа, и возвращает словарь с ними. На пропущенные
        обязательные зависимости ругается исключением.
        '''

        result = {}

        for depattr, depname in self.depsdict[name][0].items():
            assert isinstance(getattr(entity, depattr), orm.core.Required)

            # Достаём первичный ключ из дампа
            dep_pk = dump.get(depattr)
            if dep_pk is None:
                raise ValueError('Missing required dependency "{}" for entity "{}"'.format(depattr, name))

            if not isinstance(dep_pk, (tuple, list)):
                dep_pk = (dep_pk,)
            else:
                dep_pk = tuple(dep_pk)  # чтоб было не list
            if len(dep_pk) != len(self.pkmap[depname]):
                raise ValueError('Invalid primary key "{}" of dependency "{}" of entity "{}"'.format(dep_pk, depattr, name))

            # (1, 2) → {'pk1': 1, 'pk2': 2}
            dep_pk_dict = dict(zip(self.pkmap[depname], dep_pk))

            # Ищем объект в базе
            dep_obj = self.entities[depname].get(**dep_pk_dict)
            if not dep_obj:
                raise ValueError('Dependency "{}{}" for entity "{}{}" not found in database'.format(depattr, dep_pk, name, pk))

            result[depattr] = dep_obj
            del dump[depattr]

            # Если с обратной стороны была прописана опциональная зависимость,
            # она могла оказаться в кэше, так что чистим её
            self.dc_delete(name, depattr, pk, dep_pk)

        return result

    def _prepare_optional_deps(self, name, entity, pk, dump):
        '''Этот метод достаёт из базы все Optional и Set зависимости,
        пользуясь информацией из дампа, и возвращает словарь с ними. Если
        зависимости в базе не оказалось, то кладёт первичный ключ в кэш
        зависимостей, чтобы разрулить всё позже, а из дампа информацию о нём
        вычищает.
        '''

        result = {}

        for depattr, depname in list(self.depsdict[name][1].items()) + list(self.depsdict[name][2].items()):
            if depattr not in dump:
                continue

            is_set = isinstance(getattr(entity, depattr), orm.core.Set)
            assert is_set or isinstance(getattr(entity, depattr), orm.core.Optional)

            # Преобразуем к единому формату Optional и Set ключи
            dep_pks = dump.pop(depattr)
            if not is_set:
                dep_pks = [dep_pks] if dep_pks is not None else []

            elif not isinstance(dep_pks, (tuple, list, set, frozenset)):
                raise ValueError('Set dependency "{}" of entity "{}" must be iterable'.format(depattr, name))

            else:
                dep_pks = list(dep_pks)

            if not dep_pks:
                continue

            # Обрабатываем каждый ключ (для Optional он всего один, для Set неограниченно)
            if not is_set:
                assert len(dep_pks) == 1
            for dep_pk in dep_pks:
                if not isinstance(dep_pk, (tuple, list)):
                    dep_pk = (dep_pk,)
                elif isinstance(dep_pk, list):
                    dep_pk = tuple(dep_pk)
                if len(dep_pk) != len(self.pkmap[depname]):
                    raise ValueError('Invalid primary key of dependency "{}" of entity "{}"'.format(depattr, name))

                # (1, 2) → {'pk1': 1, 'pk2': 2}
                dep_pk_dict = dict(zip(self.pkmap[depname], dep_pk))

                dep_obj = self.entities[depname].get(**dep_pk_dict)

                if not dep_obj:
                    # Опциональная зависимость не найдена — подождём, кладём пока в кэш
                    self.dc_put(name, depattr, pk, dep_pk)
                    continue

                # Опциональная зависимость найдена — всё пучком
                if not is_set:
                    result[depattr] = dep_obj
                else:
                    if depattr not in result:
                        result[depattr] = []
                    result[depattr].append(dep_obj)

                # Если с обратной стороны была прописана опциональная зависимость,
                # она могла оказаться в кэше, так что чистим её
                self.dc_delete(name, depattr, pk, dep_pk)

        return result

    def json2obj(self, dump, only_create=False):
        '''Загружает объект в базу данных из указанного дампа, который должен
        быть словарём. В словаре обязательно должны быть прописаны тип объекта
        (``_entity``), все атрибуты первичного ключа и обязательные
        зависимости, которые уже должны находиться в базе данных.

        Так как некоторые значения некоторых атрибутов нельзя однозначно
        сконвертировать в JSON, поддерживаются несколько вариантов
        для некоторых типов:

        - дата и время:
          - объект datetime (без tzinfo, интерпретируется как UTC)
          - int, float как UNIX-время
          - строка в формате ``%Y-%m-%dT%H:%M:%S.%fZ``

        Возвращает словарь, содержащий:

        - ``obj`` — сам объект;
        - ``created`` — был ли объект создан в БД;
        - ``updated`` — был ли объект обновлён в БД (всегда True, если
          создан).

        :param dict dump: словарь с содержимым объекта
        :param bool only_create: если True, то не трогать уже существующие
          в базе объекты
        :rtype: dict
        '''

        name = dump.pop('_entity', '').lower()
        entity = self.entities.get(name)
        if not entity:
            raise ValueError('Unknown entity "{}"'.format(name))

        dump = dict(dump)
        pk = tuple(dump[x] for x in self.pkmap[name])

        # (1, 2) → {'pk1': 1, 'pk2': 2}
        pk_dict = dict(zip(self.pkmap[name], pk))

        # Возможно, объект уже есть в базе
        obj = entity.get(**pk_dict)
        if obj and only_create:
            return {'obj': obj, 'created': False, 'updated': False}

        # Перед тем, как создать/обновить объект, выковыриваем зависимости.
        # Могут быть зависимости, которые не прописаны у нас, но прописаны
        # с другой стороны и уже лежат в depcache. Достаём их
        relations = self._prepare_deps_from_depcache(name, entity, pk, dump)

        # Зависимости, которые были прописаны на нас в depcache, удаляются
        # из depcache.
        # Опциональные зависимости, от которых зависим мы и которые
        # отсутствуют в БД, добавляются в depcache.

        # 1) Required
        relations.update(self._prepare_required_deps(name, entity, pk, dump))

        # 2) Optional и Set
        relations.update(self._prepare_optional_deps(name, entity, pk, dump))

        dump.update(relations)
        del relations

        # Проверяем, что в dump ничего лишнего, и попутно преобразуем значения
        # некоторых атрибутов из JSON-совместимого в Python-значения
        unknown = set()
        for attr_name, value in dump.copy().items():
            if attr_name not in self.attr_names[name]:
                unknown.add(attr_name)
            if unknown:
                continue

            attr = getattr(entity, attr_name)

            if value is None:
                continue

            if attr.py_type is datetime:
                if isinstance(value, (int, float)):
                    dump[attr_name] = datetime.utcfromtimestamp(value)
                elif not isinstance(value, datetime):
                    dump[attr_name] = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')

            # TODO: date, time, timedelta

        if unknown:
            raise ValueError('Unknown attributes in dump of model "{}": {}'.format(
                name, ', '.join(unknown)
            ))

        # Данные готовы, depcache обновлён, теперь можно создать/обновить объект
        created = not obj
        updated = created
        if not obj:
            obj = entity(**dump)
            # FIXME: связи с самим собой никак не разруливаются
        else:
            assert obj.get_pk() == (pk[0] if len(pk) == 1 else pk)

            # Обновляем только изменившиеся атрибуты
            # (обновление всех подряд Pony ORM иногда не переваривает из-за Required атрибутов)
            changed_dump = {}
            for k, v in dump.items():
                if isinstance(getattr(entity, k), orm.core.Set):
                    # Для many зависимостей проверяем совпадение множеств первичных ключей
                    # FIXME: этот запрос наверняка кушает оперативку при большом кол-ве объектов
                    pks1 = set(x.get_pk() for x in getattr(obj, k).select()[:])
                    pks2 = set(x.get_pk() for x in v)
                    if pks1 != pks2:
                        changed_dump = v
                else:
                    if getattr(obj, k) != v:
                        changed_dump[k] = v

            if changed_dump:
                obj.set(**dump)
                updated = True
        obj.flush()
        return {'obj': obj, 'created': created, 'updated': updated}

    def load_entities(self, fp, chunk_sizes=None, only_create=False):
        '''Загружает дамп базы из указанного file-подобного объекта, который
        должен иметь метод readline. Генератор, yield'ит прогресс. Когда pk
        или entity будут None, значит всё.

        :param fp: file-подобный объект, из которого всё читаем
        :param dict chunk_sizes: словарь, указывающий, по сколько объектов
          указанного типа загружать в базу в рамках одной транзакции; в ключах
          название модели в lowercase, в значениях число
        :param bool only_create: если True, то не трогать уже существующие
          в базе объекты
        '''

        chunk_sizes1 = dict(self.chunk_sizes)
        if chunk_sizes:
            chunk_sizes1.update(chunk_sizes)
        chunk_sizes = chunk_sizes1
        del chunk_sizes1

        lineno = 0  # Для упрощения отладки
        current = 0  # current совпадает с lineno, если в файле нет пустых строк
        eof = False
        session_count = 0

        while not eof:
            results = []

            with orm.db_session:
                session_count = 0
                while not eof:
                    # Читаем строку из файла
                    line = fp.readline()
                    if not line:
                        eof = True
                        break
                    lineno += 1
                    line = line.strip()
                    if not line:
                        continue
                    current += 1

                    # Парсим её
                    try:
                        dump = json.loads(line)
                    except Exception as exc:
                        raise ValueError('Invalid JSON on line {}: {}'.format(lineno, str(exc)))

                    if not isinstance(dump, dict) or not dump.get('_entity') or not isinstance(dump['_entity'], str):
                        raise ValueError('Invalid dump format on line {}'.format(lineno))

                    name = dump['_entity'].lower()
                    if name not in self.entities:
                        raise ValueError('Unknown entity "{}" on line {}'.format(name, lineno))

                    # Выбираем размер сессии в зависимости от модели
                    # (если в файле модели вперемешку, то работает не так,
                    # как задумывалось, но и так сойдёт)
                    chunk_size = max(1, chunk_sizes.get(name, self.default_chunk_size))

                    # Загружаем дамп в БД
                    result = self.json2obj(dump, only_create=only_create)
                    result['entity'] = name
                    result['pk'] = result.pop('obj').get_pk()
                    result['lineno'] = lineno
                    result['current'] = current
                    results.append(result)

                    # Если сессия переполнилась, то завершаем её и создаём
                    # новую для экономии оперативной памяти
                    session_count += 1
                    if session_count >= chunk_size:
                        break  # eof is still False

            # yield'им result'ы только вне db_session, на всякий случай
            if results:
                yield results
                results = []

        yield [{'entity': None, 'created': None, 'updated': None, 'pk': None, 'lineno': lineno, 'current': current}]

    def load_from_files(self, paths=None, only_create=False, chunk_sizes=None, calc_count=True, filelist=None):
        '''Загружает дамп базы данных с указанных путей. Берутся только файлы,
        оканчивающиеся на ``_dump.jsonl`` и ``_dump.jsonl.gz`` (регистр
        не учитывается). Вложенные каталоги тоже просматриваются.

        Сущности загружаются как есть по порядку из всех файлов, зависимости
        никак не решаются. Файлы сортируются по прописанному в их именах
        названию сущности: если они загружаются в произвольном порядке, то это
        на ваш страх и риск, так как при загрузке обязательные зависимости
        могут оказаться отсутствующими.

        С целью экономии памяти вместо одной транзакции используется много,
        так что в случае сбоя база может оказаться в каком попало состоянии.
        По той же причине не рекомендуется запускать загрузку БД на работающий
        production (хотя можно, если очень осторожно и дамп гарантированно
        рабочий).

        По окончанию работы кэш опциональных зависимостей
        (``get_depcache_dict()``) должен быть пустым. Если он не пуст, значит
        какая-то опциональная зависимость не была загружена, что может быть
        не всегда хорошо.

        Генератор, yield'ит прогресс. Когда path становится None, значит всё.

        :param list paths: список файлов и каталогов, в которых искать файлы
        :param bool only_create: если True, то не трогать уже существующие
          в базе объекты
        :param dict chunk_sizes: cловарь, указывающий, по сколько объектов
          указанного типа загружать в базу в рамках одной транзакции; в ключах
          название модели в lowercase, в значениях число
        :param bool calc_count: при True считает число записей во всех файлах
          перед началом работы. Это требует полного чтения всех файлов, что
          может немного замедлить работу (особенно с gzip)
        :param set filelist: в качестве оптимизации можно скормить сюда
          результат вызова walk_all_paths — тогда аргумент paths игнорируется
        '''

        idx = {x[0]: i for i, x in enumerate(self.depmap)}  # Для последующей сортировки
        idx[''] = max(idx.values()) + 1

        if filelist is None:
            if paths is None or isinstance(paths, str):  # pragma: no cover
                raise ValueError('List of paths is required')
            filelist = self.walk_all_paths(paths)

        # Сортируем список файлов в порядке зависимостей
        filelist = list(filelist)
        filelist.sort(key=lambda x: idx[x[0]])

        # Предзагружаем число записей в каждом файле
        counts = {}  # {file_path: count}
        if calc_count:
            for _, file_path in filelist:
                cnt = 0
                if file_path.lower().endswith('.gz'):
                    fp = gzip.open(file_path, 'rt', encoding='utf-8-sig')
                else:
                    fp = open(file_path, 'r', encoding='utf-8-sig')
                with fp:
                    for line in fp:
                        if line.strip():
                            cnt += 1
                counts[file_path] = cnt
        all_count = sum(counts.values()) if counts else None

        for _, file_path in filelist:
            count = counts.get(file_path)
            if file_path.lower().endswith('.gz'):
                fp = gzip.open(file_path, 'rt', encoding='utf-8-sig')
            else:
                fp = open(file_path, 'r', encoding='utf-8-sig')
            with fp:
                for results in self.load_entities(fp, chunk_sizes=chunk_sizes, only_create=only_create):
                    for result in results:
                        result['path'] = file_path
                        result['count'] = count
                        result['all_count'] = all_count
                    yield results

        yield [{'path': None, 'entity': None, 'pk': None, 'created': None, 'updated': None, 'count': all_count, 'all_count': all_count}]

    def walk_all_paths(self, paths):
        '''Вспомогательный метод. Возвращает множество файлов, найденных
        по указанным путям (разрешаются файлы и каталоги, всё вложенное тоже
        просматривается), и имена моделей, выдранные из их имён.
        '''

        filelist = set()  # [(entity_name or '', path)]

        for path in paths:
            path = os.path.abspath(path)

            if os.path.isdir(path):
                walk = os.walk(path)
            else:
                walk = ([os.path.dirname(path), [], [os.path.split(path)[-1]]],)

            for subpath, _, files in walk:
                for f in files:
                    if not f.lower().endswith('_dump.jsonl') and not f.lower().endswith('_dump.jsonl.gz'):
                        continue

                    # Парсим имя файла как имя сущности, чтобы загружать в порядке зависимостей
                    entity = f.lower().rsplit('_', 1)[0]
                    if entity not in self.entities:
                        entity = ''

                    filelist.add((entity, os.path.join(subpath, f)))

        return filelist


def get_entities_dict(entities):
    '''Возвращает словарь имя:модель для запрашиваемых моделей.

    :param entities: список моделей или объект Database, из которой достать
      модели
    :rtype: dict
    '''

    if isinstance(entities, orm.core.Database):
        # Если скормили базу данных, то просто берём все её модели
        return {k.lower(): v for k, v in entities.entities.items()}

    # Если же список моделей, то придётся повозиться, чтобы достать их
    # имена: модели в себе свои имена почему-то не хранят
    entities_dict = {}
    db = None
    for e in entities:
        if db is None:
            db = e._database_
        elif e._database_ is not db:
            raise ValueError('Entities from different databases are not allowed')

        ok = False
        for k, v in db.entities.items():
            if v is e:
                entities_dict[k.lower()] = e
                ok = True
                break
        assert ok

    return entities_dict
