#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.sorting import CATEGORY, CHARACTER, CHARACTER_GROUP


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


class CharacterBL(BaseBL):
    def create(self, author, data):
        data = Validator(CHARACTER).validated(data)

        errors = {}

        exist_character = self.model.get(name=data['name'])
        if exist_character:
            errors['name'] = [lazy_gettext('Character already exists')]

        from mini_fiction.models import CharacterGroup

        group = CharacterGroup.get(id=data['group'])
        if not group:
            errors['group'] = [lazy_gettext('Group not found')]

        if errors:
            raise ValidationError(errors)

        character = self.model(**data)
        character.flush()
        return character

    def update(self, author, data):
        data = Validator(CHARACTER).validated(data, update=True)
        character = self.model

        errors = {}

        if 'name' in data:
            from mini_fiction.models import Character
            exist_character = Character.get(name=data['name'])
            if exist_character and exist_character.id != character.id:
                errors['name'] = [lazy_gettext('Character already exists')]

        if 'group' in data:
            from mini_fiction.models import CharacterGroup

            group = CharacterGroup.get(id=data['group'])
            if not group:
                errors['group'] = [lazy_gettext('Group not found')]
        else:
            group = None

        if errors:
            raise ValidationError(errors)

        for key, value in data.items():
            setattr(character, key, value)

        return character

    def delete(self, author):
        self.model.delete()


class CharacterGroupBL(BaseBL):
    def create(self, author, data):
        data = Validator(CHARACTER_GROUP).validated(data)

        exist_group = self.model.get(name=data['name'])
        if exist_group:
            raise ValidationError({'name': [lazy_gettext('Group already exists')]})

        group = self.model(**data)
        group.flush()
        return group

    def update(self, author, data):
        data = Validator(CHARACTER_GROUP).validated(data, update=True)
        group = self.model

        if 'name' in data:
            from mini_fiction.models import CharacterGroup
            exist_group = CharacterGroup.get(name=data['name'])
            if exist_group and exist_group.id != group.id:
                raise ValidationError({'name': [lazy_gettext('Group already exists')]})

        for key, value in data.items():
            setattr(group, key, value)

        return group

    def delete(self, author):
        self.model.delete()
