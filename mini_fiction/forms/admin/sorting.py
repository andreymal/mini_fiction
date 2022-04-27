#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import StringField, TextAreaField
from flask_wtf.file import FileField

from pony import orm

from mini_fiction.models import CharacterGroup
from mini_fiction.forms.form import Form
from mini_fiction.forms.fields import LazySelectField


class CharacterForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = StringField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    picture = FileField(
        lazy_gettext('Picture'),
        render_kw=attrs_dict,
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )

    group = LazySelectField(
        lazy_gettext('Group'),
        choices=lambda: list(orm.select((x.id, x.name) for x in CharacterGroup)),
        coerce=int,
    )


class CharacterGroupForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = StringField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )
