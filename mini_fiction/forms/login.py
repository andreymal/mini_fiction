#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from flask_wtf import Form
from wtforms import TextField, PasswordField, validators


class LoginForm(Form):
    username = TextField(lazy_gettext('Username'), [validators.Required(), validators.Length(min=1, max=32)])
    password = PasswordField(lazy_gettext('Password'), [validators.Required()])
