#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from wtforms import StringField, PasswordField, validators

from mini_fiction.forms.form import Form


attrs_dict = {'class': 'required input-xlarge'}


class AuthorRegistrationForm(Form):
    username = StringField(
        'Логин',
        render_kw=dict(attrs_dict, maxlength=32),
    )
    email = StringField(
        'Электропочта',
        render_kw=dict(attrs_dict, maxlength=75),
        description='Адрес электронной почты для активации аккаунта'
    )
    password = PasswordField(
        'Пароль',
        [validators.EqualTo('password2', message=lazy_gettext('Passwords do not match'))],
        render_kw=attrs_dict,
        description='Выбирайте сложный пароль'
    )
    password2 = PasswordField(
        'Пароль (опять)',
        [validators.DataRequired()],
        render_kw=attrs_dict,
        description='Повторите пароль, чтобы не забыть'
    )


class AuthorPasswordResetForm(Form):
    email = StringField(
        'Ваш e-mail',
        [
            validators.DataRequired(),
            validators.Length(min=6, max=75),
            validators.Email('Введите правильный адрес электронной почты.')
        ],
        render_kw=dict(attrs_dict, maxlength=75),
    )


class AuthorNewPasswordForm(Form):
    attrs_dict = {'class': 'input-xlarge'}

    new_password1 = PasswordField(
        "",
        [
            validators.DataRequired('Поле нельзя оставить пустым'),
            validators.EqualTo('new_password2', message=lazy_gettext('Passwords do not match'))
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
    )

    new_password2 = PasswordField(
        "",
        [
            validators.DataRequired('Поле нельзя оставить пустым'),
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
    )
