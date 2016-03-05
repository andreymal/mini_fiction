#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import TextField, PasswordField

from mini_fiction.forms.form import Form


class LoginForm(Form):
    username = TextField(lazy_gettext('Username'))
    password = PasswordField(lazy_gettext('Password'))
