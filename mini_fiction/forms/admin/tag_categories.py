#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import TextField, TextAreaField

from mini_fiction.forms.form import Form


class TagCategoryForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    name = TextField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=256),
    )

    color = TextField(
        lazy_gettext('Color'),
        render_kw=dict(attrs_dict, maxlength=7, type='text'),
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )
