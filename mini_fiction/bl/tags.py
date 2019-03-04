#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import re
from datetime import datetime

from flask import current_app
from flask_babel import lazy_gettext
from pony import orm

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.tags import TAG
from mini_fiction.utils.misc import normalize_tag, call_after_request as later


class TagBL(BaseBL):
    def get_tags_objects(
        self, tags, create=False, user=None, resolve_aliases=True,
        resolve_blacklisted=True, create_if_errors=False
    ):
        """Принимает список объектов Tag или строк с названиями тегов
        (можно вперемешку) и возвращает словарь со следующими ключами:

        - success — True, если всё хорошо (в списке tags гарантированно
          отсутствуют None);

        - tags — список из объектов Tag, которые были успешно найдены
          (соответствует порядку исходному списку tags, вместо ненайденных
          тегов стоит None);

        - aliases — список тегов, оказавшихся алиасами и заменённых
          на каноничные теги (пуст при resolve_aliases=False);

        - blacklisted — список заблокированных тегов, не попавших в tags
          (пуст при resolve_blacklisted=False);

        - invalid — список строк, которые не являются синтаксически
          корректными тегами (например, пустая строка), и причин
          некорректности (кортежи из двух элементов);

        - created — список свежесозданных тегов, если они создавались
          (при create=True);

        - nonexisting — список из строк, для которых тегов не нашлось
          (при create=False).

        Если скормить несколько одинаковых тегов, то в списке tags могут
        появиться дубликаты.
        """

        from mini_fiction.validation.utils import safe_string_coerce
        from mini_fiction.models import Tag

        # Достаём список строк для поиска тегов
        tags_search = [x for x in tags if not isinstance(x, Tag)]
        tags_db = {x.iname: x for x in tags if isinstance(x, Tag)}

        # Ищем недостающие теги в базе
        inames = [normalize_tag(x) for x in tags_search]
        inames = [x for x in inames if x]
        if inames:
            tags_db.update({x.iname: x for x in Tag.select(lambda t: t.iname in inames).prefetch(Tag.is_alias_for)})

        result = {
            'success': True,
            'tags': [None] * len(tags),
            'aliases': [],
            'blacklisted': [],
            'invalid': [],
            'created': [],
            'nonexisting': [],
        }

        create_tags = []  # [(index, name, iname), ...]

        # Анализируем каждый запрошенный тег
        for i, x in enumerate(tags):
            if isinstance(x, Tag):
                name = x.name
                iname = x.iname
                tag = x
            else:
                name = safe_string_coerce(x.strip())
                iname = normalize_tag(name)
                tag = tags_db.get(iname)
                assert iname == normalize_tag(x)

            if tag:
                # Если тег существует, проверяем, что его можно использовать
                if resolve_aliases and tag.is_alias_for:
                    if tag.is_alias_for.is_alias_for:
                        raise RuntimeError('Tag alias {} refers to another alias {}!'.format(tag.id, tag.is_alias_for.id))
                    result['aliases'].append(tag)
                    tag = tag.is_alias_for
                if resolve_blacklisted and tag.is_blacklisted:
                    result['blacklisted'].append(tag)
                    result['success'] = False
                    tag = None

            elif create:
                # Если не существует — создаём
                if not user or not user.is_authenticated:
                    raise ValueError('Not authenticated')
                reason = self.validate_tag_name(name)
                if reason is not None:
                    result['invalid'].append((x, reason))
                    result['success'] = False
                else:
                    create_tags.append((i, name, iname))  # Отложенное создание тегов

            else:
                result['nonexisting'].append(x)
                result['success'] = False

            if tag:
                result['tags'][i] = tag

        # Если нужно создать теги, то создаём их только при отсутствии других
        # ошибок, чтобы зазря не мусорить в базу данных (проверка отключается
        # опцией create_if_errors=True)
        if create_tags and (create_if_errors or result['success']):
            for i, name, iname in create_tags:
                if iname in tags_db:
                    # На случай, если пользователь пропихнул дублирующиеся теги
                    result['tags'][i] = tags_db[iname]
                    continue
                tag = Tag(name=name, iname=iname, created_by=user)
                tag.flush()  # получаем id у базы данных
                tags_db[tag.iname] = tag  # На случай, если у следующего тега в цикле совпадёт iname
                result['created'].append(tag)
                result['tags'][i] = tag

            # see views/tags.py
            current_app.cache.delete('tags_autocomplete_default')

        return result

    def get_all_tags(self, only_main=False, sort=False):
        from mini_fiction.models import Tag

        q = Tag.select()
        q = q.filter(lambda x: not x.is_blacklisted and not x.is_alias)
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

    def get_tags_with_categories(self, sort='name'):
        from mini_fiction.models import Tag

        categories_dict = {}

        tags = list(Tag.select(lambda x: not x.is_blacklisted and not x.is_alias).prefetch(Tag.category))
        if sort == 'stories':
            tags.sort(key=lambda tag: tag.published_stories_count, reverse=True)
        elif sort == 'date':
            tags.sort(key=lambda tag: tag.created_at, reverse=True)
        elif sort == 'name':
            tags.sort(key=lambda tag: tag.iname)
        else:
            raise ValueError('Invalid tags sorting: {!r}'.format(sort))

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
        """Принимает множество строк и возвращает словарь запрещённых тегов
        с описанием причины запрета. Если ничего не запрещено, словарь пуст.
        """

        from mini_fiction.models import Tag

        result = {}
        inames = []

        # Проверяем корректность синтаксиса
        for x in tags:
            reason = self.validate_tag_name(x)
            if reason is not None:
                result[x] = reason
                inames.append(None)
            else:
                iname = normalize_tag(x)
                if not iname:
                    result[x] = lazy_gettext('Empty tag')
                inames.append(iname)

        # Проверяем чёрный список в базе данных
        inames_for_search = [x for x in inames if x]
        if inames_for_search:
            bl_tags = {t.iname: t for t in orm.select(
                x for x in Tag if x.iname in inames_for_search and x.is_blacklisted
            )}
            for x, iname in zip(tags, inames):
                if iname in bl_tags:
                    result[x] = bl_tags[iname].reason_to_blacklist

        return result

    def search_by_prefix(self, name, with_aliases=True, limit=20):
        from mini_fiction.models import Tag

        iname = normalize_tag(name)
        if not iname or limit < 1:
            return []
        if limit > 100:
            limit = 100

        result = []

        # Ищем точное совпадение
        exact_tag = Tag.get(iname=iname, is_alias_for=None, reason_to_blacklist='')
        if exact_tag:
            result.append(exact_tag)
        elif with_aliases:
            tag_alias = exact_tag = Tag.get(iname=iname, reason_to_blacklist='')
            if tag_alias:
                exact_tag = tag_alias.is_alias_for
                assert exact_tag
                result.append(exact_tag)

        # Ищем остальные теги по префиксу
        if len(result) < limit:
            tags = set(Tag.select(
                lambda x: x.iname.startswith(iname) and not x.is_alias and not x.is_blacklisted
            ).order_by(Tag.published_stories_count.desc())[:limit + len(result)])
            if with_aliases:
                # Подключаем синонимы, если разрешили
                # (отдельным запросом, чтоб были по порядку ниже несинонимов)
                tags = tags | set(Tag.select(
                    lambda x: x.iname.startswith(iname) and x.is_alias and not x.is_blacklisted
                ))
            tags = sorted(tags, key=lambda x: x.published_stories_count, reverse=True)
            result.extend([x for x in tags if x not in result])

        return result[:limit]

    def get_aliases_for(self, tags, hidden=False):
        from mini_fiction.models import Tag

        for x in tags:
            if x.is_alias or x.is_blacklisted:
                raise ValueError('Only valid canonical tags are allowed for get_aliases_for')

        result = {x.id: [] for x in tags}
        q = Tag.select(lambda x: x.is_alias_for in tags)
        if not hidden:
            q = q.filter(lambda x: not x.is_hidden_alias)
        for ts in q:
            result[ts.is_alias_for.id].append(ts)
        return result

    def validate_tag_name(self, name):
        iname = normalize_tag(name)
        if not iname:
            return lazy_gettext('Empty tag')

        for regex, reason in current_app.config['TAGS_BLACKLIST_REGEX'].items():
            if re.search(regex, iname, flags=re.IGNORECASE):
                return reason

        return None

    def create(self, user, data):
        from mini_fiction.models import Tag, AdminLog

        if not user or not user.is_staff:
            raise ValueError('Not authorized')

        data = Validator(TAG).validated(data)

        errors = {}

        bad_reason = self.validate_tag_name(data['name'])
        if bad_reason:
            errors['name'] = [bad_reason]

        iname = normalize_tag(data['name'])
        if not bad_reason and Tag.get(iname=iname):
            errors['name'] = [lazy_gettext('Tag already exists')]

        canonical_tag = None
        if data.get('is_alias_for'):
            canonical_tag = Tag.get(iname=normalize_tag(data['is_alias_for']))
            if not canonical_tag:
                errors['is_alias_for'] = [lazy_gettext('Tag not found')]

        if errors:
            raise ValidationError(errors)

        tag = Tag(
            name=data['name'],
            iname=iname,
            category=data.get('category'),
            color=data.get('color') or '',
            description=data.get('description') or '',
            is_main_tag=data.get('is_main_tag', False),
            created_by=user,
            is_alias_for=None,
            reason_to_blacklist='',
        )
        tag.flush()

        AdminLog.bl.create(user=user, obj=tag, action=AdminLog.ADDITION)

        if data.get('reason_to_blacklist'):
            tag.bl.set_blacklist(user, data['reason_to_blacklist'])
        elif canonical_tag:
            tag.bl.make_alias_for(user, canonical_tag, hidden=data.get('is_hidden_alias', False))

        return tag

    def update(self, user, data):
        from mini_fiction.models import Tag, AdminLog

        if not user or not user.is_staff:
            raise ValueError('Not authorized')

        tag = self.model

        data = Validator(TAG).validated(data, update=True)
        changes = {}
        errors = {}

        if 'name' in data and data['name'] != tag.name:
            bad_reason = self.validate_tag_name(data['name'])
            if bad_reason:
                errors['name'] = [bad_reason]

            iname = normalize_tag(data['name'])
            if not bad_reason and iname != tag.iname and Tag.get(iname=iname):
                errors['name'] = [lazy_gettext('Tag already exists')]

            changes['name'] = data['name']
            if iname != tag.iname:
                changes['iname'] = iname

        if 'category' in data:
            old_category_id = tag.category.id if tag.category else None
            if old_category_id != data['category']:
                changes['category'] = data['category']

        for key in ('color', 'description', 'is_main_tag'):
            if key in data and data[key] != getattr(tag, key):
                changes[key] = data[key]

        canonical_tag = tag.is_alias_for
        if 'is_alias_for' in data:
            if data.get('is_alias_for'):
                canonical_tag = Tag.get(iname=normalize_tag(data['is_alias_for']))
                if not canonical_tag:
                    errors['is_alias_for'] = [lazy_gettext('Tag not found')]
                elif canonical_tag == tag:
                    errors['is_alias_for'] = [lazy_gettext('Tag cannot refer to itself')]
            else:
                canonical_tag = None

        if errors:
            raise ValidationError(errors)
        if changes:
            changes['updated_at'] = datetime.utcnow()
            tag.set(**changes)

            AdminLog.bl.create(
                user=user,
                obj=tag,
                action=AdminLog.CHANGE,
                fields=set(changes) - {'updated_at'},
            )

        if 'reason_to_blacklist' in data:
            self.set_blacklist(user, data['reason_to_blacklist'])
        if not tag.is_blacklisted and ('is_alias_for' in data or 'is_hidden_alias' in data):
            self.make_alias_for(user, canonical_tag, data.get('is_hidden_alias', tag.is_hidden_alias))

    def set_blacklist(self, user, reason):
        from mini_fiction.models import StoryTag, StoryTagLog, AdminLog

        if not user or not user.is_staff:
            raise ValueError('Not authorized')

        tag = self.model
        if reason == tag.reason_to_blacklist:
            return

        old_reason = tag.reason_to_blacklist
        tm = datetime.utcnow()

        if reason:
            tag.reason_to_blacklist = reason
            tag.is_alias_for = None
            tag.is_hidden_alias = False

            story_tags = list(StoryTag.select(lambda x: x.tag == tag))
            for st in story_tags:
                StoryTagLog(
                    story=st.story.id,
                    tag=tag,
                    tag_name=tag.name,
                    action_flag=StoryTagLog.DELETION,
                    modified_by=user,
                    date=tm,
                ).flush()
                # FIXME: кажется, следующая строчка должна находиться не здесь, но я ленивый
                later(current_app.tasks['sphinx_update_story'].delay, st.story.id, ('tag',))
                st.delete()

        else:
            tag.reason_to_blacklist = ''

        tag.updated_at = tm

        if tag.reason_to_blacklist and old_reason:
            log_message = 'Изменена причина попадания тега в чёрный список.'
        elif tag.reason_to_blacklist:
            log_message = 'Тег добавлен в чёрный список.'
        else:
            log_message = 'Тег убран из чёрного списка.'
        AdminLog.bl.create(
            user=user,
            obj=tag,
            action=AdminLog.CHANGE,
            change_message=log_message,
        )

    def make_alias_for(self, user, canonical_tag, hidden=False):
        from mini_fiction.models import StoryTag, StoryTagLog, AdminLog

        if not user or not user.is_staff:
            raise ValueError('Not authorized')

        if canonical_tag and canonical_tag.is_alias_for:
            if canonical_tag.is_alias_for.is_alias_for:
                raise RuntimeError('Tag alias {} refers to another alias {}!'.format(canonical_tag.id, canonical_tag.is_alias_for.id))
            canonical_tag = canonical_tag.is_alias_for

        tag = self.model
        if tag.is_alias_for == canonical_tag:
            if canonical_tag and bool(hidden) != tag.is_hidden_alias:
                tag.is_hidden_alias = bool(hidden)
                tag.updated_at = datetime.utcnow()
                AdminLog.bl.create(
                    user=user,
                    obj=tag,
                    action=AdminLog.CHANGE,
                    fields=('is_hidden_alias',),
                )
            return

        tm = datetime.utcnow()

        if canonical_tag:
            if canonical_tag == tag:
                raise RuntimeError('Self-reference!')

            tag.is_alias_for = canonical_tag
            tag.is_hidden_alias = bool(hidden)

            story_tags = list(StoryTag.select(lambda x: x.tag == tag))
            stories_with_canonical_tag = list(orm.select(x.story.id for x in StoryTag if x.tag == canonical_tag))
            for st in story_tags:
                StoryTagLog(
                    story=st.story.id,
                    tag=tag,
                    tag_name=tag.name,
                    action_flag=StoryTagLog.DELETION,
                    modified_by=user,
                    date=tm,
                ).flush()
                if st.story.id not in stories_with_canonical_tag:
                    StoryTagLog(
                        story=st.story.id,
                        tag=canonical_tag,
                        tag_name=canonical_tag.name,
                        action_flag=StoryTagLog.ADDITION,
                        modified_by=user,
                        date=tm,
                    ).flush()
                    st.tag = canonical_tag
                    st.flush()
                else:
                    st.delete()
                later(current_app.tasks['sphinx_update_story'].delay, st.story.id, ('tag',))

        else:
            tag.is_alias_for = None
            tag.is_hidden_alias = False

        tag.updated_at = tm

        if tag.is_alias_for:
            log_message = 'Тег стал синонимом тега «{}».'.format(tag.is_alias_for.name)
        else:
            log_message = 'Тег перестал быть синонимом.'
        AdminLog.bl.create(
            user=user,
            obj=tag,
            action=AdminLog.CHANGE,
            change_message=log_message,
        )
