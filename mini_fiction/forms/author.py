#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from flask import current_app, g
from flask_babel import lazy_gettext
from wtforms import TextField, TextAreaField, PasswordField, SelectField, IntegerField, FieldList, FormField, validators

from mini_fiction.models import Category
from mini_fiction.forms.form import Form
from mini_fiction.forms.fields import LazySelectField, LazySelectMultipleField
from mini_fiction.widgets import StoriesButtons, ContactsWidget


class ContactForm(Form):
    name = LazySelectField(
        '',
        [validators.Required()],
        choices=lambda: [
            (x['name'], x['label'].get(g.locale.language) or x['label']['default'])
            for x in current_app.config['CONTACTS']
        ],
    )
    value = TextField(
        '',
        [validators.Optional()],
    )


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

    contacts = FieldList(
        FormField(ContactForm),
        'Контакты',
        widget=ContactsWidget(),
        render_kw={'class': 'contacts-form'},
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
