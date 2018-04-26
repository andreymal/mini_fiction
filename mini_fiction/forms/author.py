#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from flask import current_app, g
from flask_babel import lazy_gettext
from wtforms import TextField, TextAreaField, PasswordField, SelectField, IntegerField
from wtforms import BooleanField, FileField, FieldList, FormField, validators

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
    attrs_bio_dict = {'class': 'input-xxxlarge with-markitup'}

    avatar = FileField(
        lazy_gettext('Avatar'),
        render_kw=dict(attrs_dict, accept='image/*'),
        description=lazy_gettext('The recommended size is 100x100 pixels'),
    )

    delete_avatar = BooleanField(
        lazy_gettext('Delete avatar'),
    )

    bio = TextAreaField(
        'Пару слов о себе',
        [
            validators.Optional(),
            validators.Length(max=2048)
        ],
        render_kw=dict(attrs_bio_dict, placeholder='Небольшое описание, отображается в профиле', cols=40, rows=10),
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

    comments_per_page = IntegerField(
        '',
        [
            validators.InputRequired(),
            validators.NumberRange(min=1, max=1000),
        ],
        render_kw=dict(attrs_dict, type='number', min=1, max=1000),
    )

    comments_maxdepth = IntegerField(
        '',
        [
            validators.InputRequired(),
            validators.NumberRange(min=0, max=32767),
        ],
        render_kw=dict(attrs_dict, type='number', min=0, max=32767),
    )

    comment_spoiler_threshold = IntegerField(
        '',
        [
            validators.InputRequired(),
            validators.NumberRange(min=-32768, max=32767),
        ],
        render_kw=dict(attrs_dict, type='number', min=-32768, max=32767),
    )

    header_mode = SelectField(
        '',
        [],
        choices=[(0, 'Скрыть'), (1, 'Показать без рассказов'), (2, 'Показать с рассказами')],
        coerce=int,
        widget=StoriesButtons(),
        render_kw=radio_attrs,
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


class AuthorEditSubscriptionsForm(Form):
    attrs_dict = {'class': 'input-xlarge'}

    email_abuse_report = BooleanField()
    email_story_pubrequest = BooleanField()
    email_story_publish_noappr = BooleanField()
    email_story_delete = BooleanField()

    email_story_publish = BooleanField()
    tracker_story_publish = BooleanField()

    email_story_draft = BooleanField()
    tracker_story_draft = BooleanField()

    email_story_reply = BooleanField()
    tracker_story_reply = BooleanField()

    email_story_lreply = BooleanField()
    tracker_story_lreply = BooleanField()

    email_news_reply = BooleanField()
    tracker_news_reply = BooleanField()
