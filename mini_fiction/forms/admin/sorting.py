#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import TextField, TextAreaField
from flask_wtf.file import FileField

from pony import orm

from mini_fiction.models import CharacterGroup
from mini_fiction.forms.form import Form
from mini_fiction.forms.fields import LazySelectField


class CategoryForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = TextField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )

    color = TextField(
        lazy_gettext('Color'),
        render_kw=dict(attrs_dict, maxlength=7, type='color'),
    )


class CharacterForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = TextField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    picture = FileField(
        lazy_gettext('Picture'),
        description=lazy_gettext('PNG only'),
        render_kw=dict(attrs_dict, accept='image/png'),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )

    group = LazySelectField(
        lazy_gettext('Group'),
        choices=lambda: orm.select((x.id, x.name) for x in CharacterGroup)[:],
        coerce=int,
    )


class CharacterGroupForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = TextField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )


class ClassifierForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = TextField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )
