#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Markup, current_app
from wtforms import TextAreaField, ValidationError

from mini_fiction.forms.form import Form


class CommentForm(Form):
    attrs_dict = {'class': 'span4 with-markitup js-form-saving'}

    text = TextAreaField(
        '',
        render_kw=dict(attrs_dict, data_formsaving='comment', data_formgroup='comment', maxlength=8192, placeholder='Текст нового комментария', id='id_text', rows=10, cols=40)
    )

    def validate_text(self, field):
        # TODO: а как вот это на cerberus перенести?
        if len(Markup(field.data).striptags()) < current_app.config['COMMENT_MIN_LENGTH']:
            raise ValidationError('Сообщение слишком короткое!')
