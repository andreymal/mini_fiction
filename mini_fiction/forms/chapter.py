#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from wtforms import TextField, TextAreaField, validators

from mini_fiction.forms.form import Form


class ChapterForm(Form):
    """ Форма добавления новой главы к рассказу """
    textarea_dict = {'class': 'input-xxxlarge chapter-textarea with-markitup js-form-saving'}
    attrs_dict = {'class': 'input-xxxlarge js-form-saving'}

    title = TextField(
        'Название',
        [
            validators.Length(min=0, max=512)
        ],
        render_kw=dict(attrs_dict, data_formsaving='chapter_title', data_formgroup='chapter', maxlength=512, placeholder='Заголовок главы (необязательно)')
    )

    notes = TextAreaField(
        'Заметки',
        [
            validators.Length(max=4096)
        ],
        render_kw=dict(textarea_dict, data_formsaving='chapter_notes', data_formgroup='chapter', placeholder='Заметки к главе', cols=40, rows=4, id='id_notes'),
        description='Заметки автора к главе'
    )

    text = TextAreaField(
        'Текст главы',
        [
            validators.Length(max=300000)
        ],
        render_kw=dict(textarea_dict, data_formsaving='chapter_text', data_formgroup='chapter', placeholder='Текст новой главы', cols=40, rows=10, id='id_text'),
    )
