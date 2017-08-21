#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import BooleanField, TextField, TextAreaField
from flask_wtf.file import FileField

from mini_fiction.forms.form import Form


class LogopicForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    picture = FileField(
        lazy_gettext('Picture'),
        render_kw=dict(attrs_dict, accept='image/*'),
    )

    visible = BooleanField(
        lazy_gettext('Show on site'),
        render_kw=attrs_dict,
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )

    original_link = TextField(
        lazy_gettext('Link to original'),
        render_kw=dict(attrs_dict, maxlength=255),
    )

    original_link_label = TextAreaField(
        lazy_gettext('Labels for link to original'),
        description=lazy_gettext('One per line. Format: "lang=label" (for specified language) or just "label" (to set default value)'),
        render_kw=dict(attrs_dict, maxlength=255),
    )
