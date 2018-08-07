#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask import current_app, render_template
from flask_babel import lazy_gettext
from pony import orm

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.utils.misc import normalize_tag


class TagBL(BaseBL):
    def get_tags_objects(self, tags, create=False, user=None):
        """Принимает список объектов Tag или строк с названиями тегов
        и возвращает список только объектов Tag (порядок сохраняется).
        Если create=False, то вместо несуществующих тегов добавляет None.
        Если create=True, но создать тег не получается, кидает ошибку
        ValueError. user указывает, от чьего имени будет создан тег.
        Умеет разруливать синонимы.
        """

        from mini_fiction.validation.utils import safe_string_coerce
        from mini_fiction.models import Tag, TagAlias, TagBlacklist

        # Достаём список строк для поиска тегов
        tags_search = [x for x in tags if not isinstance(x, Tag)]

        # Ищем недостающие теги в базе
        inames = [normalize_tag(x) for x in tags_search]
        inames = [x for x in inames if x]
        tags_db = {}
        if inames:
            tags_db = {x.iname: x for x in Tag.select(lambda t: t.iname in inames)}

        # Ищем синонимы
        inames = set(inames) - set(tags_db)
        if inames:
            tags_db.update({x.iname: x.tag for x in TagAlias.select(
                lambda ts: ts.iname in inames
            ).prefetch(TagAlias.tag)})

        # Загружаем чёрный список тегов
        inames_for_create = None
        blacklist = []
        if create:
            inames_for_create = set(inames) - set(tags_db)
            if inames_for_create:
                blacklist = list(orm.select(
                    x.iname for x in TagBlacklist if x.iname in inames_for_create
                ))

        # Собираем результат, попутно создавая недостающие теги
        result = []
        for x in tags:
            if isinstance(x, Tag):
                result.append(x)
                continue

            x = safe_string_coerce(x).strip()
            iname = normalize_tag(x)

            if iname in tags_db:
                result.append(tags_db[iname])

            elif create:
                if not user or not user.is_authenticated:
                    raise ValueError('Not authenticated')
                if iname in blacklist:
                    raise ValueError('Tag {!r} is blacklisted'.format(iname))
                if not x or not iname:
                    raise ValueError('Tag {!r} is not valid'.format(x))
                tag = Tag(name=x, iname=iname, created_by=user)
                tag.flush()  # получаем id у базы данных
                result.append(tag)

            else:
                result.append(None)

        assert len(tags) == len(result)
        return result

    def get_all_tags(self, only_main=False, sort=False):
        from mini_fiction.models import Tag

        q = Tag.select()
        if only_main:
            q = q.filter(lambda x: x.is_main_tag)

        q = q.prefetch(Tag.category)
        tags = list(q)
        if sort:
            tags.sort(key=lambda x: (x.category.id if x.category else 2 ** 31, x.iname))
        return tags

    def get_categories(self, prefetch_tags=True):
        from mini_fiction.models import TagCategory

        q = TagCategory.select()
        if prefetch_tags:
            q = q.prefetch(TagCategory.tags)
        categories = list(q)
        return categories

    def get_tags_with_categories(self):
        from mini_fiction.models import Tag

        categories_dict = {}

        tags = list(Tag.select().prefetch(Tag.category))
        tags.sort(key=lambda tag: tag.published_stories_count, reverse=True)

        categories_dict = {}
        others = {'category': None, 'tags': []}
        for tag in tags:
            if not tag.category:
                others['tags'].append(tag)
                continue
            if tag.category.id not in categories_dict:
                categories_dict[tag.category.id] = {'category': tag.category, 'tags': []}
            categories_dict[tag.category.id]['tags'].append(tag)

        result = sorted(categories_dict.values(), key=lambda x: x['category'].id)
        result.append(others)
        return result

    def get_blacklisted_tags(self, tags):
        """Принимает множество строк и возвращает те из них, которые являются
        запрещёнными.
        """

        from mini_fiction.models import TagBlacklist

        inames = [normalize_tag(x) for x in tags]
        inames_for_search = [x for x in inames if x]
        blacklist = set(orm.select(
            x.iname for x in TagBlacklist if x.iname in inames_for_search
        ))

        result = []
        for name, iname in zip(tags, inames):
            if not iname or iname in blacklist:
                result.append(name)

        return result

    def search_by_prefix(self, name, with_aliases=True, limit=20):
        from mini_fiction.models import Tag, TagAlias

        iname = normalize_tag(name)
        if not iname or len(iname) > 32 or limit < 1:
            return []
        if limit > 100:
            limit = 100

        result = []

        # Ищем точное совпадение
        exact_tag = Tag.get(iname=iname)
        if exact_tag:
            result.append(exact_tag)
        elif with_aliases:
            exact_tag = orm.select(x.tag for x in TagAlias if x.iname == iname).first()
            if exact_tag:
                result.append(exact_tag)

        # Ищем остальные теги по префиксу
        if len(result) < limit:
            tags = set(Tag.select(
                lambda x: x.iname.startswith(iname)
            ).order_by(Tag.published_stories_count.desc())[:limit + len(result)])
            if with_aliases:
                # Подключаем синонимы, если разрешили
                tags = tags | set(orm.select(
                    x.tag for x in TagAlias if x.iname.startswith(iname)
                ))
            tags = sorted(tags, key=lambda x: x.published_stories_count, reverse=True)
            result.extend([x for x in tags if x not in result])

        return result[:limit]

    def get_aliases_for(self, tags):
        from mini_fiction.models import TagAlias

        result = {x.id: [] for x in tags}
        for ts in TagAlias.select(lambda x: x.tag in tags):
            result[ts.tag.id].append(ts)
        return result
