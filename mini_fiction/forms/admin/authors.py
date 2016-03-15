#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import BooleanField, TextField

from mini_fiction.forms.form import Form


class AdminAuthorForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    email = TextField(
        lazy_gettext('Email'),
        render_kw=dict(attrs_dict, maxlength=75),
    )

    is_active = BooleanField(
        lazy_gettext('Is active'),
        render_kw=attrs_dict,
        description=lazy_gettext("Inactive users can't log in"),
    )

    is_staff = BooleanField(
        lazy_gettext('Is staff'),
        render_kw=attrs_dict,
        description=lazy_gettext('Staff can approve stories and partially administer the site'),
    )

    is_superuser = BooleanField(
        lazy_gettext('Is superuser'),
        render_kw=attrs_dict,
        description=lazy_gettext('Superuser can fully administer the site'),
    )
