#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.tag_categories import TAG_CATEGORY


class TagCategoryBL(BaseBL):
    def create(self, author, data):
        data = Validator(TAG_CATEGORY).validated(data)

        exist_tag_category = self.model.get(name=data['name'])
        if exist_tag_category:
            raise ValidationError({'name': [lazy_gettext('Tag category already exists')]})

        tag_category = self.model(**data)
        tag_category.flush()
        log_addition(by=author, what=tag_category)

        return tag_category

    def update(self, author, data):
        data = Validator(TAG_CATEGORY).validated(data, update=True)
        tag_category = self.model

        if 'name' in data:
            from mini_fiction.models import TagCategory
            exist_tag_category = TagCategory.get(name=data['name'])
            if exist_tag_category and exist_tag_category.id != tag_category.id:
                raise ValidationError({'name': [lazy_gettext('Tag category already exists')]})

        changed_fields = set()
        for key, value in data.items():
            if getattr(tag_category, key) != value:
                setattr(tag_category, key, value)
                changed_fields |= {key,}

        if changed_fields:
            log_changed_fields(by=author, what=tag_category, fields=sorted(changed_fields))

        return tag_category

    def delete(self, author):
        log_deletion(by=author, what=self.model)
        self.model.delete()
