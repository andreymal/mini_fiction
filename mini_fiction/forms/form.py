#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from wtforms import FormField, FieldList
from flask_wtf import FlaskForm as BaseForm


class Form(BaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.non_field_errors = []

    def set_errors(self, external_errors):
        for name, errors in external_errors.items():
            if not errors:
                continue
            field = self._fields.get(name)
            if field is None:
                self.non_field_errors.extend(errors)
                continue
            if field.errors:
                field.errors = list(field.errors) + list(errors)
            else:
                field.errors = list(errors)
            if isinstance(field, FieldList):
                for i, e in errors.items():
                    if isinstance(field.entries[i], FormField):
                        field.entries[i].set_errors(e)
                    else:
                        field.entries[i].errors = list(e)
        self._errors = None  # pylint: disable=W0201
