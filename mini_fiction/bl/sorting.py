#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.sorting import CATEGORY


class CategoryBL(BaseBL):
    def create(self, author, data):
        data = Validator(CATEGORY).validated(data)

        exist_category = self.model.get(name=data['name'])
        if exist_category:
            raise ValidationError({'name': [lazy_gettext('Category already exists')]})

        category = self.model(**data)
        category.flush()
        return category

    def update(self, author, data):
        data = Validator(CATEGORY).validated(data, update=True)
        category = self.model

        if 'name' in data:
            from mini_fiction.models import Category
            exist_category = Category.get(name=data['name'])
            if exist_category and exist_category.id != category.id:
                raise ValidationError({'name': [lazy_gettext('Category already exists')]})

        for key, value in data.items():
            setattr(category, key, value)

        return category

    def delete(self, author):
        self.model.delete()
