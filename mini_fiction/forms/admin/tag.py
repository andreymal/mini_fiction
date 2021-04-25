#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import TextField, TextAreaField, BooleanField

from pony import orm

from mini_fiction.models import TagCategory
from mini_fiction.forms.form import Form
from mini_fiction.forms.fields import LazySelectField
from mini_fiction.widgets import TagsInput


class TagForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}
    attrs_tags_dict = {'class': 'input-xxxlarge', 'autocomplete': 'off'}

    name = TextField(
        'Название',
        render_kw=dict(attrs_dict, maxlength=256),
    )

    category = LazySelectField(
        'Категория',
        choices=lambda: [(0, '-')] + list(orm.select((x.id, x.name) for x in TagCategory)),
        coerce=int,
    )

    color = TextField(
        lazy_gettext('Color'),
        render_kw=dict(attrs_dict, maxlength=7, type='text'),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )

    is_main_tag = BooleanField(
        'Основной тег',
        render_kw=attrs_dict,
        description='Основные теги не скрываются за многоточием в списке тегов рассказа',
    )

    is_alias_for = TextField(
        'Синоним для',
        render_kw=dict(attrs_tags_dict, maxlength=512),
        description='Впишите название основного тега. На него будет заменён тег-синоним у всех рассказов',
    )

    is_hidden_alias = BooleanField(
        'Скрытый синоним',
        render_kw=attrs_dict,
        description='Не показывать в списке синонимов на странице тега, чтобы не смущать пользователей',
    )

    is_extreme_tag = BooleanField(
        'Экстремальный тег',
        render_kw=attrs_dict,
        description='Этим тегом обозначается что-то совсем жёсткое',
    )

    reason_to_blacklist = TextField(
        'Блокировка тега',
        render_kw=dict(attrs_dict, maxlength=256),
        description='Впишите причину, чтобы заблокировать тег. Тег будет удалён у всех рассказов',
    )
