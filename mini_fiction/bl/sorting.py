# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from flask import current_app
from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.sorting import CHARACTER, CHARACTER_FOR_UPDATE, CHARACTER_GROUP
from mini_fiction.utils.image import save_image, ImageKind


class CharacterBL(BaseBL):
    def create(self, author, data):
        from mini_fiction.models import AdminLog

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
        picture_metadata = save_image(kind=ImageKind.CHARACTERS, data=picture)

        character = self.model(picture='pending', sha256sum='pending', **data)
        character.flush()

        self.model.picture = picture_metadata.relative_path
        self.model.sha256sum = picture_metadata.sha256sum

        character.bl.set_picture_data(picture)
        AdminLog.bl.create(user=author, obj=character, action=AdminLog.ADDITION)

        return character

    def update(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(CHARACTER_FOR_UPDATE).validated(data, update=True)
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

        changed_fields = set()

        if data.get('picture'):
            picture = self.validate_and_get_picture_data(data['picture'])
        else:
            picture = None

        for key, value in data.items():
            if key == 'picture':
                if picture is not None:
                    self.set_picture_data(picture)
                    changed_fields |= {'picture',}
            elif key == 'group':
                if character.group.id != value:
                    setattr(character, key, value)
                    changed_fields |= {key,}
            elif getattr(character, key) != value:
                setattr(character, key, value)
                changed_fields |= {key,}

        if changed_fields:
            AdminLog.bl.create(
                user=author,
                obj=character,
                action=AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )

        return character

    def delete(self, author):
        from mini_fiction.models import AdminLog
        AdminLog.bl.create(user=author, obj=self.model, action=AdminLog.DELETION)
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


class CharacterGroupBL(BaseBL):
    def create(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(CHARACTER_GROUP).validated(data)

        exist_group = self.model.get(name=data['name'])
        if exist_group:
            raise ValidationError({'name': [lazy_gettext('Group already exists')]})

        group = self.model(**data)
        group.flush()
        AdminLog.bl.create(user=author, obj=group, action=AdminLog.ADDITION)
        return group

    def update(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(CHARACTER_GROUP).validated(data, update=True)
        group = self.model

        if 'name' in data:
            from mini_fiction.models import CharacterGroup
            exist_group = CharacterGroup.get(name=data['name'])
            if exist_group and exist_group.id != group.id:
                raise ValidationError({'name': [lazy_gettext('Group already exists')]})

        changed_fields = set()
        for key, value in data.items():
            if getattr(group, key) != value:
                setattr(group, key, value)
                changed_fields |= {key,}

        if changed_fields:
            AdminLog.bl.create(
                user=author,
                obj=group,
                action=AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )

        return group

    def delete(self, author):
        from mini_fiction.models import AdminLog
        AdminLog.bl.create(user=author, obj=self.model, action=AdminLog.DELETION)
        self.model.delete()
