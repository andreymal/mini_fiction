#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext, lazy_pgettext
from wtforms import SelectField, StringField, TextAreaField, BooleanField
from pony import orm

from mini_fiction.models import Character, Rating
from mini_fiction.forms.fields import LazySelectField, LazySelectMultipleField, GroupedModelChoiceField, StringListField
from mini_fiction.widgets import StoriesCharacterSelect, StoriesButtons, TagsInput
from mini_fiction.forms.form import Form


pgettext = lazy_pgettext  # avoid pybabel extract problem


class StoryForm(Form):
    attrs_dict = {'class': 'input-xxxlarge'}
    attrs_markitup_dict = {'class': 'input-xxxlarge', 'data-bazooka': 'RichEditor'}
    attrs_tags_dict = {'class': 'input-xxxlarge', 'autocomplete': 'off'}
    img_attrs = {
           'group_container_class': 'characters-group group-',
           'input_attrs': {'class': 'hidden'},
           'container_attrs': {'class': 'character-item'}
    }

    radio_attrs = {
       'btn_attrs': {'type': 'button', 'class': 'btn'},
       'input_attrs': {'class': 'hidden'},
       'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-radio'},
       'input_container_attrs': {'class': 'buttons-data'},
    }

    checkbox_attrs = {
       'btn_attrs': {'type': 'button', 'class': 'btn'},
       'input_attrs': {'class': 'hidden'},
       'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-checkbox'},
       'input_container_attrs': {'class': 'buttons-data'},
    }

    title = StringField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=512, placeholder=lazy_gettext('Title of the new story'))
    )

    tags = StringListField(
        lazy_gettext('Tags'),
        render_kw=dict(attrs_tags_dict, maxlength=512, placeholder=lazy_gettext('Tags are separated by commas, for example: Fluff, Daily, Sketch')),
        description=lazy_gettext(
            'List genres and main events of the story. You can create '
            'new tags if there are not enough existing ones'
        ),
        widget=TagsInput(),
    )

    characters = GroupedModelChoiceField(
        lazy_gettext('Characters'),
        [],
        choices=lambda: list(Character.select().prefetch(Character.group).order_by(Character.group, Character.id)),
        choices_attrs=('id', 'name'),
        coerce=int,
        group_by_field='group',
        render_kw=img_attrs,
        widget=StoriesCharacterSelect(multiple=True),
        description=lazy_gettext(
            'You should choose characters who are in the thick of things, '
            'not all those mentioned in the story.'
        ),
    )

    summary = TextAreaField(
        lazy_gettext('Short story description'),
        render_kw=dict(attrs_dict, cols=40, rows=10, maxlength=4096, placeholder=lazy_gettext('Required short story description')),
    )

    notes = TextAreaField(
        lazy_gettext('Notes'),
        render_kw=dict(attrs_markitup_dict, id='id_notes', cols=40, rows=10, maxlength=4096, placeholder=lazy_gettext('Notes to the story')),
    )

    original_url = StringField(
        lazy_gettext('Link to original (if any)'),
        render_kw=dict(attrs_dict, maxlength=255, placeholder='http://'),
        description=lazy_gettext("Don't forget to add it if you are not a direct author of the story"),
    )

    original_title = StringField(
        lazy_gettext('Original title'),
        render_kw=dict(attrs_dict, maxlength=255),
    )

    original_author = StringField(
        lazy_gettext('Original author'),
        render_kw=dict(attrs_dict, maxlength=255),
    )

    rating = LazySelectField(
        pgettext('story_info', 'Rating'),
        choices=lambda: list(orm.select((x.id, x.name) for x in Rating).order_by(-1)),
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )

    original = SelectField(
        pgettext('story_info', 'Origin'),
        choices=[
            (1, pgettext('story_origin', 'Original')),
            (0, pgettext('story_origin', 'Translation')),
        ],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )

    status = SelectField(
        pgettext('story_info', 'Status'),
        choices=[
            (0, pgettext('story_info', 'Incomplete')),
            (1, pgettext('story_info', 'Complete')),
            (2, pgettext('story_info', 'Freezed')),
        ],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
        description=lazy_gettext('Activity of the story (is it being written now)'),
    )

    minor = BooleanField('', default=False)
