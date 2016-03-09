#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Markup, current_app
from flask_wtf import Form
from wtforms import TextAreaField, ValidationError, validators


class CommentForm(Form):
    attrs_dict = {'class': 'span4 with-markitup'}

    text = TextAreaField(
        'Название',
        [validators.Length(max=8192)],
        render_kw=dict(attrs_dict, maxlength=8192, placeholder='Текст нового комментария', id='id_text', rows=10, cols=40)
    )

    def validate_text(self, field):
        if len(Markup(field.data).striptags()) < current_app.config['COMMENT_MIN_LENGTH']:
            raise ValidationError('Сообщение слишком короткое!')
