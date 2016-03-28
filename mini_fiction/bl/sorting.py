#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import os

from flask import current_app
from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.sorting import CATEGORY, CHARACTER, CHARACTER_GROUP, CLASSIFIER


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

        picture = self.validate_and_get_picture_data(data.pop('picture'))

        character = self.model(**data)
        character.flush()
        character.bl.set_picture_data(picture)
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

        if data.get('picture'):
            picture = self.validate_and_get_picture_data(data['picture'])
        else:
            picture = None

        for key, value in data.items():
            if key == 'picture':
                if picture is not None:
                    self.set_picture_data(picture)
            else:
                setattr(character, key, value)

        return character

    def delete(self, author):
        self.model.delete()

    def validate_and_get_picture_data(self, picture):
        fp = picture.stream
        header = fp.read(4)
        if header != b'\x89PNG':
            raise ValidationError({'picture': [lazy_gettext('PNG only')]})
        data = header + fp.read(16384 - 4 + 1)  # 16 KiB + 1 byte for validation
        if len(data) > 16384:
            raise ValidationError({'picture': [
                lazy_gettext('Maximum picture size is {maxsize} KiB').format(maxsize=16)
            ]})
        return data

    def set_picture_data(self, data):
        filename = str(self.model.id) + '.png'
        pathset = ('characters', filename)
        urlpath = '/'.join(pathset)  # equivalent to ospath except Windows!
        ospath = os.path.join(current_app.config['MEDIA_ROOT'], *pathset)

        dirpath = os.path.dirname(ospath)
        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)

        with open(ospath, 'wb') as fp:
            fp.write(data)

        self.model.picture = urlpath
        return urlpath


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


class ClassifierBL(BaseBL):
    def create(self, author, data):
        data = Validator(CLASSIFIER).validated(data)

        exist_classifier = self.model.get(name=data['name'])
        if exist_classifier:
            raise ValidationError({'name': [lazy_gettext('Classifier already exists')]})

        classifier = self.model(**data)
        classifier.flush()
        return classifier

    def update(self, author, data):
        data = Validator(CLASSIFIER).validated(data, update=True)
        classifier = self.model

        if 'name' in data:
            from mini_fiction.models import Classifier
            exist_classifier = Classifier.get(name=data['name'])
            if exist_classifier and exist_classifier.id != classifier.id:
                raise ValidationError({'name': [lazy_gettext('Classifier already exists')]})

        for key, value in data.items():
            setattr(classifier, key, value)

        return classifier

    def delete(self, author):
        self.model.delete()
