#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_babel import lazy_gettext
from flask_wtf import Form, RecaptchaField
from wtforms import TextField, PasswordField, validators


attrs_dict = {'class': 'required input-xlarge'}
username_field = TextField(
        'Логин',
        [
            validators.Required(),
            validators.Length(min=1, max=32),
            validators.Regexp(
                r'^[0-9a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u0401_@+-.. ]+$',
                message='Пожалуйста, исправьте ошибку в логине - он может содержать только русские/латинские буквы, цифры, пробел, точку и символы _ @ + -',
            )
        ],
        render_kw=dict(attrs_dict, maxlength=32),
        description='Только русские/латинские буквы, цифры, пробел, точка и символы _ @ + -'
    )


class AuthorRegistrationForm(Form):
    username = username_field
    email = TextField(
        'Электропочта',
        [
            validators.Required(),
            validators.Length(min=6, max=75),
            validators.Email('Пожалуйста, исправьте ошибку в адресе e-mail: похоже, он неправильный')
        ],
        render_kw=dict(attrs_dict, maxlength=75),
        description='Адрес электронной почты для активации аккаунта'
    )
    password1 = PasswordField(
        'Пароль',
        [
            validators.Required(),
            validators.EqualTo('password2', message=lazy_gettext('Passwords do not match'))
        ],
        render_kw=attrs_dict,
        description='Выбирайте сложный пароль'
    )
    password2 = PasswordField(
        'Пароль (опять)',
        [validators.Required()],
        render_kw=attrs_dict,
        description='Повторите пароль, чтобы не забыть'
    )


class AuthorRegistrationCaptchaForm(AuthorRegistrationForm):
    recaptcha = RecaptchaField(
        'Капча'
    )


class AuthorPasswordResetForm(Form):
    email = TextField(
        'Ваш e-mail',
        [
            validators.Required(),
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
            validators.Required('Поле нельзя оставить пустым'),
            validators.EqualTo('new_password2', message=lazy_gettext('Passwords do not match'))
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
    )

    new_password2 = PasswordField(
        "",
        [
            validators.Required('Поле нельзя оставить пустым'),
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
    )
