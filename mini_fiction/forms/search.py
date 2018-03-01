#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from wtforms import Form
from wtforms import SelectField, SelectMultipleField, TextField, BooleanField, IntegerField, validators
from pony import orm

from mini_fiction.models import Category, Character, Rating, Classifier
from mini_fiction.forms.fields import LazySelectMultipleField, GroupedModelChoiceField
from mini_fiction.widgets import StoriesCharacterSelect, StoriesCheckboxSelect, StoriesCategorySelect, StoriesButtons, ButtonWidget


class SearchForm(Form):
    checkbox_attrs = {
        'btn_attrs': {'type': 'button', 'class': 'btn'},
        'data_attrs': {'class': 'hidden'},
        'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-checkbox'},
        'data_container_attrs': {'class': 'buttons-data'},
    }
    radio_attrs = {
        'btn_attrs': {'type': 'button', 'class': 'btn'},
        'data_attrs': {'class': 'hidden'},
        'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-radio'},
        'data_container_attrs': {'class': 'buttons-data'},
    }
    img_attrs = {
        'group_container_class': 'characters-group group-',
        'data_attrs': {'class': 'hidden'},
        'container_attrs': {'class': 'character-item'}
    }

    # Строка поиска
    q = TextField(
        '',
        [
            validators.Length(max=128)
        ],
        render_kw={
            'size': 32,
            'placeholder': 'Пинки-поиск',
            'id': 'appendedInputButtons',
            'class': 'span3',
            'maxlength': 128,
        }
    )

    # Галочка включения расширенного синтаксиса поиска
    extsyntax = BooleanField('', default=True)

    # Минимальный размер
    min_words = IntegerField(
        '',
        [validators.Optional()],
        render_kw={
            'size': 8,
            'placeholder': 'От',
            'class': 'span3',
            'maxlength': 8,
            'min': 0,
            'max': 99999000,
            'type': 'number',
        }
    )

    # Максимальный размер
    max_words = IntegerField(
        '',
        [validators.Optional()],
        render_kw={
            'size': 8,
            'placeholder': 'До',
            'class': 'span3',
            'maxlength': 8,
            'min': 0,
            'max': 99999000,
            'type': 'number',
        }
    )

    # Жанры
    genre = LazySelectMultipleField(
        '',
        [],
        choices=lambda: orm.select((x.id, x.name) for x in Category)[:],
        widget=StoriesCategorySelect(multiple=True),
        description='',
        coerce=int,
        render_kw={
            'label_attrs': ['checkbox', 'inline', 'gen'],
        }
    )

    # Персонажи
    char = GroupedModelChoiceField(
        '',
        [],
        choices=lambda: Character.select().prefetch(Character.group).order_by(Character.group, Character.id)[:],
        choices_attrs=('id', 'name'),
        coerce=int,
        group_by_field='group',
        render_kw=img_attrs,
        widget=StoriesCharacterSelect(multiple=True),
    )

    # Оригинал/перевод
    original = SelectMultipleField(
        '',
        [],
        choices=[(0, 'Перевод'), (1, 'Оригинал')],
        coerce=int,
        widget=StoriesButtons(multiple=True),
        render_kw=checkbox_attrs,
    )

    # Статус рассказа
    finished = SelectMultipleField(
        '',
        [],
        choices=[(0, 'Не завершен'), (1, 'Завершен')],
        coerce=int,
        widget=StoriesButtons(multiple=True),
        render_kw=checkbox_attrs,
    )

    # Активность рассказа
    freezed = SelectMultipleField(
        '',
        [],
        choices=[(0, 'Активен'), (1, 'Заморожен')],
        coerce=int,
        widget=StoriesButtons(multiple=True),
        render_kw=checkbox_attrs,
    )

    # Рейтинги
    rating = LazySelectMultipleField(
        '',
        [],
        choices=lambda: orm.select((x.id, x.name) for x in Rating).order_by(-1)[:],
        coerce=int,
        widget=StoriesButtons(multiple=True),
        render_kw=checkbox_attrs,
    )

    # События
    cls = LazySelectMultipleField(
        '',
        [],
        choices=lambda: orm.select((x.id, x.name) for x in Classifier)[:],
        widget=StoriesCheckboxSelect(multiple=True),
        coerce=int,
        render_kw={'label_attrs': ['checkbox', 'inline']}
    )

    # Кнопка "Развернуть тонкие настройки поиска"
    button_advanced = BooleanField(
        '',
        [],
        widget=ButtonWidget(),
        render_kw={
            'type': 'button',
            'class': 'btn btn-collapse',
            'data-toggle': 'collapse',
            'data-target': '#more-info',
            'text': 'Еще более тонкий поиск'
        }
    )

    # Кнопка "Развернуть фильтры"
    button_filters = BooleanField(
        '',
        [],
        widget=ButtonWidget(),
        render_kw={
            'type': 'button',
            'class': 'btn btn-collapse',
            'data-toggle': 'collapse',
            'data-target': '#more-filters',
            'text': 'Фильтры поиска'
        }
    )

    # Кнопка "Развернуть сортировку"
    button_sort = BooleanField(
        '',
        [],
        widget=ButtonWidget(),
        render_kw={
            'type': 'button',
            'class': 'btn btn-collapse',
            'data-toggle': 'collapse',
            'data-target': '#more-sort',
            'text': 'Сортировка результатов'
        }
    )

    # Сортировка
    sort = SelectField(
        '',
        [validators.InputRequired()],
        choices=[(0, 'По релевантности'), (1, 'По дате'), (2, 'По размеру'), (3, 'По рейтингу'), (4, 'По комментам'), (5, 'Случайно')],
        widget=StoriesButtons(),
        coerce=int,
        render_kw=radio_attrs,
    )

    # Тип поиска
    type = SelectField(
        '',
        [validators.InputRequired()],
        choices=[(0, 'По описанию'), (1, 'По главам')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )
