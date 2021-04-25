#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import BooleanField, IntegerField, TextField, TextAreaField, validators

from mini_fiction.forms.form import Form


class HtmlBlockForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}
    attrs_dict_short = {'class': 'input'}
    attrs_markitup_dict = {'class': 'input-xxlarge with-markitup'}

    name = TextField(
        lazy_gettext('Name'),
        render_kw=dict(attrs_dict, maxlength=64),
    )

    lang = TextField(
        lazy_gettext('Language (leave empty to make this block default)'),
        render_kw=dict(attrs_dict, maxlength=4, placeholder='en / ru / jp etc.'),
    )

    is_template = BooleanField(
        lazy_gettext('Is Jinja2 template'),
        render_kw=attrs_dict,
        description=lazy_gettext(
            'Be careful when editing the template! Jinja2 is very powerful, '
            'and you may accidentally break something or create a vulnerability.'
        ),
    )

    cache_time = IntegerField(
        lazy_gettext('Cache time (seconds)'),
        [
            validators.InputRequired(),
            validators.NumberRange(min=0, max=259200),
        ],
        render_kw=dict(attrs_dict_short, type='number', min=0, max=259200),
        description=lazy_gettext(
            'How long the rendered content will be stored in the cache '
            '(0 — do not cache). The cache is shared for all users'
        )
    )

    title = TextField(
        lazy_gettext('Title'),
        render_kw=dict(attrs_dict, maxlength=255),
    )

    content = TextAreaField(
        lazy_gettext('Content'),
        render_kw=attrs_markitup_dict,
    )
