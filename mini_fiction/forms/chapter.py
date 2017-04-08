#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from wtforms import TextField, TextAreaField, StringField, validators

from mini_fiction.forms.form import Form
from mini_fiction.widgets import ServiceButtonWidget


class ChapterForm(Form):
    """ Форма добавления новой главы к рассказу """
    textarea_dict = {'class': 'input-xxlarge chapter-textarea with-markitup'}
    attrs_dict = {'class': 'input-xxlarge'}

    title = TextField(
        'Название',
        [
            validators.Required('Пожалуйста, назовите новую главу вашего рассказа'),
            validators.Length(min=1, max=512)
        ],
        render_kw=dict(attrs_dict, maxlength=512, placeholder='Заголовок новой главы')
    )

    notes = TextAreaField(
        'Заметки',
        [
            validators.Length(max=4096)
        ],
        render_kw=dict(textarea_dict, placeholder='Заметки к главе', cols=40, rows=4, id='id_notes'),
        description='Заметки автора к главе'
    )

    text = TextAreaField(
        'Текст главы',
        [
            validators.Length(max=300000)
        ],
        render_kw=dict(textarea_dict, placeholder='Текст новой главы', cols=40, rows=10, id='id_text'),
    )
