#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import BooleanField, TextField, TextAreaField

from mini_fiction.forms.form import Form


class HtmlBlockForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}
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

    content = TextAreaField(
        lazy_gettext('Content'),
        render_kw=attrs_markitup_dict,
    )
