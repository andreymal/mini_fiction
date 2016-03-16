#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from flask_babel import lazy_gettext
from flask_wtf import Form
from wtforms import TextField, TextAreaField, PasswordField, SelectField, IntegerField, validators

from mini_fiction.models import Category
from mini_fiction.forms.fields import LazySelectMultipleField
from mini_fiction.widgets import StoriesButtons


class AuthorEditProfileForm(Form):
    attrs_dict = {'class': 'input-xlarge'}

    bio = TextAreaField(
        'Пару слов о себе',
        [
            validators.Optional(),
            validators.Length(max=2048)
        ],
        render_kw=dict(attrs_dict, placeholder='Небольшое описание, отображается в профиле', cols=40, rows=10),
    )

    jabber = TextField(
        'Jabber ID (XMPP)',
        [
            validators.Optional(),
            validators.Email('Пожалуйста, исправьте ошибку в адресе jabber: похоже, он неправильный'),
            validators.Length(max=75),
        ],
        render_kw=dict(attrs_dict, maxlength=75, placeholder='Адрес jabber-аккаунта'),
        description='Пример: user@server.com',
    )

    skype = TextField(
        'Skype ID',
        [
            validators.Optional(),
            validators.Regexp(r'^[a-zA-Z0-9\._-]+$', message='Пожалуйста, исправьте ошибку в логине skype: похоже, он неправильный'),
            validators.Length(max=32),
        ],
        render_kw=dict(attrs_dict, maxlength=32, placeholder='Логин skype'),
    )

    tabun = TextField(
        'Логин на Табуне',
        [
            validators.Optional(),
            validators.Regexp(r'^[a-zA-Z0-9-_]+$', message='Пожалуйста, исправьте ошибку в имени пользователя: похоже, оно неправильно'),
            validators.Length(max=32),
        ],
        render_kw=dict(attrs_dict, maxlength=32),
    )

    forum = TextField(
        'Профиль на Форуме',
        [
            validators.Optional(),
            validators.Length(max=72),
        ],
        render_kw=dict(attrs_dict, maxlength=32, placeholder='URL вашего профиля'),
        description='Вставьте полную ссылку на профиль',
    )

    vk = TextField(
        'Логин ВКонтакте',
        [
            validators.Optional(),
            validators.Regexp(r'^[a-zA-Z0-9\._-]+$', message='Пожалуйста, исправьте ошибку в логине ВК: похоже, он неправильный'),
            validators.Length(max=32),
        ],
        render_kw=dict(attrs_dict, maxlength=32),
    )


class AuthorEditPrefsForm(Form):
    attrs_dict = {'class': 'input-small'}
    checkbox_attrs = {
        'btn_attrs': {'type': 'button', 'class': 'btn'},
        'data_attrs': {'class': 'hidden'},
        'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-checkbox'},
        'data_container_attrs': {'class': 'buttons-data'},
    }
    radio_attrs = {
        'btn_attrs': {'type': 'button', 'class': 'btn'},
        'data_attrs': {'class': 'hidden'},
        'btn_container_attrs': {'class': 'btn-group buttons-visible', 'data-toggle': 'buttons-radio'},
        'data_container_attrs': {'class': 'buttons-data'},
    }

    excluded_categories = LazySelectMultipleField(
        '',
        [],
        choices=lambda: orm.select((x.id, x.name) for x in Category).order_by(1)[:],
        coerce=int,
        widget=StoriesButtons(multiple=True),
        render_kw=checkbox_attrs,
    )

    detail_view = SelectField(
        '',
        [],
        choices=[(0, 'Кратко'), (1, 'Подробно')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )

    nsfw = SelectField(
        '',
        [],
        choices=[(0, 'Показать'), (1, 'Скрыть')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
    )

    comments_maxdepth = IntegerField(
        '',
        [
            validators.InputRequired(),
        ],
        render_kw=dict(attrs_dict, type='number', min=0),
    )

    comment_spoiler_threshold = IntegerField(
        '',
        [
            validators.InputRequired(),
        ],
        render_kw=dict(attrs_dict, type='number'),
    )


class AuthorEditEmailForm(Form):
    attrs_dict = {'class': 'input-xlarge'}

    email = TextField(
        'Электропочта',
        [
            validators.Required(),
            validators.Email('Пожалуйста, исправьте ошибку в адресе e-mail: похоже, он неправильный'),
            validators.Length(max=75),
        ],
        render_kw=dict(attrs_dict, maxlength=75, placeholder='Адрес электронной почты'),
    )

    password = PasswordField(
        "Пароль",
        [
            validators.Required(),
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
        description='Для безопасной смены почты введите пароль',
    )


class AuthorEditPasswordForm(Form):
    attrs_dict = {'class': 'input-xlarge'}

    old_password = PasswordField(
        "Старый пароль",
        [
            validators.Required('Поле нельзя оставить пустым'),
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
        description='Для безопасной смены пароля введите старый пароль',
    )

    new_password_1 = PasswordField(
        "Новый пароль",
        [
            validators.Required('Поле нельзя оставить пустым'),
            validators.EqualTo('new_password_2', message=lazy_gettext('Passwords do not match'))
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
        description='Выбирайте сложный пароль',
    )

    new_password_2 = PasswordField(
        "Новый пароль (опять)",
        [
            validators.Required('Поле нельзя оставить пустым'),
        ],
        render_kw=dict(attrs_dict, placeholder='****************'),
        description='Повторите новый пароль, чтобы не забыть',
    )
