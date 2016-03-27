#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from wtforms import SelectField, TextField, TextAreaField, validators
from pony import orm

from mini_fiction.models import Category, Character, Rating, Classifier
from mini_fiction.forms.fields import LazySelectField, LazySelectMultipleField, GroupedModelChoiceField
from mini_fiction.widgets import StoriesCharacterSelect, StoriesCheckboxSelect, StoriesCategorySelect, StoriesButtons
from mini_fiction.forms.form import Form


class StoryForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}
    attrs_markitup_dict = {'class': 'input-xxlarge with-markitup'}
    img_attrs = {
           'group_container_class': 'characters-group group-',
           'data_attrs': {'class': 'hidden'},
           'container_attrs': {'class': 'character-item'}
    }

    radio_attrs = {
       'btn_attrs': {'type': 'button', 'class': 'btn'},
       'data_attrs': {'class': 'hidden'},
       'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-radio'},
       'data_container_attrs': {'class': 'buttons-data'},
    }

    checkbox_attrs = {
       'btn_attrs': {'type': 'button', 'class': 'btn'},
       'data_attrs': {'class': 'hidden'},
       'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-checkbox'},
       'data_container_attrs': {'class': 'buttons-data'},
    }

    title = TextField(
        'Название',
        render_kw=dict(attrs_dict, maxlength=512, placeholder='Заголовок нового рассказа')
    )

    categories = LazySelectMultipleField(
        'Жанры',
        choices=lambda: orm.select((x.id, x.name) for x in Category)[:],
        widget=StoriesCategorySelect(multiple=True),
        description='',
        coerce=int,
        render_kw={'label_attrs': ['checkbox', 'inline', 'gen']}
    )

    characters = GroupedModelChoiceField(
        'Персонажи',
        [],
        choices=lambda: Character.select().prefetch(Character.group).order_by(Character.group, Character.id)[:],
        choices_attrs=('id', 'name'),
        coerce=int,
        group_by_field='group',
        render_kw=img_attrs,
        widget=StoriesCharacterSelect(multiple=True),
        description='Следует выбрать персонажей, находящихся в гуще событий, а не всех пони, упомянутых в произведении.',
    )

    summary = TextAreaField(
        'Краткое описание рассказа',
        render_kw=dict(attrs_dict, cols=40, rows=10, maxlength=4096, placeholder='Обязательное краткое описание рассказа'),
    )

    notes = TextAreaField(
        'Заметки',
        render_kw=dict(attrs_markitup_dict, id='id_notes', cols=40, rows=10, maxlength=4096, placeholder='Заметки к рассказу'),
    )

    source_link = TextField(
        'Ссылка на источник (если есть)',
        render_kw=dict(attrs_dict, maxlength=255, placeholder='http://')
    )

    source_title = TextField(
        'Название источника',
        render_kw=dict(attrs_dict, maxlength=255)
    )

    rating = LazySelectField(
        'Рейтинг',
        choices=lambda: orm.select((x.id, x.name) for x in Rating).order_by(-1)[:],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )

    original = SelectField(
        'Происхождение',
        choices=[(1, 'Оригинал'), (0, 'Перевод')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )

    freezed = SelectField(
        'Состояние',
        choices=[(0, 'Активен'), (1, 'Заморожен')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
        description='Активность рассказа (пишется ли он сейчас)'
    )

    finished = SelectField(
        'Статус',
        choices=[(0, 'Не закончен'), (1, 'Закончен')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
        description='Завершен ли рассказ'
    )

    classifications = LazySelectMultipleField(
        'События',
        choices=lambda: orm.select((x.id, x.name) for x in Classifier)[:],
        widget=StoriesCheckboxSelect(multiple=True),
        description='Ключевые события рассказа',
        coerce=int,
        render_kw={'label_attrs': ['checkbox', 'inline']}
    )
