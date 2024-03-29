#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from wtforms import Form
from wtforms import SelectField, SelectMultipleField, StringField, BooleanField, IntegerField, RadioField, validators
from pony import orm

from mini_fiction.models import Character, Rating
from mini_fiction.forms.fields import LazySelectMultipleField, GroupedModelChoiceField, StringListField
from mini_fiction.widgets import StoriesCharacterSelect, StoriesButtons, ButtonWidget, TagsInput


class SearchForm(Form):
    checkbox_attrs = {
        'btn_attrs': {'type': 'button', 'class': 'btn'},
        'input_attrs': {'class': 'hidden'},
        'btn_container_attrs': {'class': 'btn-group btn-group-wrap buttons-visible', 'data-toggle': 'buttons-checkbox'},
        'input_container_attrs': {'class': 'buttons-data'},
    }
    radio_attrs = {
        'btn_attrs': {'type': 'button', 'class': 'btn'},
        'input_attrs': {'class': 'hidden'},
        'btn_container_attrs': {'class': 'btn-group btn-group-wrap buttons-visible', 'data-toggle': 'buttons-radio'},
        'input_container_attrs': {'class': 'buttons-data'},
    }
    img_attrs = {
        'group_container_class': 'characters-group group-',
        'input_attrs': {'class': 'hidden'},
        'container_attrs': {'class': 'character-item'}
    }
    attrs_tags_dict = {'class': 'input-xxxlarge', 'autocomplete': 'off'}

    # Строка поиска
    q = StringField(
        '',
        [
            validators.Length(max=128)
        ],
        render_kw={
            'size': 32,
            'placeholder': 'Пинки-поиск',
            'class': 'search-input',
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

    tags = StringListField(
        'Теги',
        render_kw=dict(attrs_tags_dict, maxlength=512, placeholder='Теги разделяются запятой, например: Флафф, Повседневность, Зарисовка'),
        widget=TagsInput(),
    )

    tags_mode = RadioField(
        'Режим поиска тегов',
        choices=[
            ('all', 'Рассказы со всеми тегами'),
            ('any', 'Рассказы с любым из тегов'),
        ],
        default='all',
    )

    exclude_tags = StringListField(
        'Исключить рассказы с этими тегами',
        render_kw=dict(attrs_tags_dict, maxlength=512, placeholder='Теги разделяются запятой, например: Флафф, Повседневность, Зарисовка'),
        widget=TagsInput(),
    )

    # Персонажи
    char = GroupedModelChoiceField(
        '',
        [],
        choices=lambda: list(Character.select().prefetch(Character.group).order_by(Character.group, Character.id)),
        choices_attrs=('id', 'name'),
        coerce=int,
        group_by_field='group',
        render_kw=img_attrs,
        widget=StoriesCharacterSelect(multiple=True),
    )

    char_mode = RadioField(
        'Режим поиска персонажей',
        choices=[
            ('all', 'Рассказы со всеми персонажами'),
            ('any', 'Рассказы с любым из персонажей'),
        ],
        default='all',
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
        choices=lambda: list(orm.select((x.id, x.name) for x in Rating).order_by(-1)),
        coerce=int,
        widget=StoriesButtons(multiple=True),
        render_kw=checkbox_attrs,
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
