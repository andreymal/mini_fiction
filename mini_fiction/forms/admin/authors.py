#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask_babel import lazy_gettext
from wtforms import BooleanField, StringField, SelectField, PasswordField, validators

from mini_fiction.forms.form import Form


class AdminAuthorForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}

    email = StringField(
        lazy_gettext('Email'),
        render_kw=dict(attrs_dict, maxlength=75),
    )

    is_active = BooleanField(
        lazy_gettext('Is active'),
        render_kw=attrs_dict,
        description=lazy_gettext("Only active accounts can log in"),
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

    premoderation_mode = SelectField(
        lazy_gettext('Premoderation mode'),
        choices=[
            ('', lazy_gettext('Default')),
            ('on', lazy_gettext('Enable premoderation')),
            ('off', lazy_gettext('Disable premoration (verified author)')),
        ]
    )

    ban_reason = StringField(
        lazy_gettext('Ban reason'),
        render_kw=dict(attrs_dict, placeholder=lazy_gettext('This text will be displayed when a user tries to log into an inactive account')),
    )


class AdminEditPasswordForm(Form):
    attrs_dict = {'class': 'input-xlarge'}

    new_password_1 = PasswordField(
        "Новый пароль",
        [
            validators.DataRequired('Поле нельзя оставить пустым'),
            validators.EqualTo('new_password_2', message=lazy_gettext('Passwords do not match'))
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
        description='Выбирайте сложный пароль',
    )

    new_password_2 = PasswordField(
        "Новый пароль (опять)",
        [
            validators.DataRequired('Поле нельзя оставить пустым'),
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
        description='Повторите новый пароль',
    )
