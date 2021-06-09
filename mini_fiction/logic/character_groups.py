from flask_babel import lazy_gettext

from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.models import Author, CharacterGroup
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.sorting import CHARACTER_GROUP


def create(author: Author, data: RawData) -> CharacterGroup:
    data = Validator(CHARACTER_GROUP).validated(data)

    exist_group = CharacterGroup.get(name=data["name"])
    if exist_group:
        raise ValidationError({"name": [lazy_gettext("Group already exists")]})

    group = CharacterGroup(**data)
    group.flush()
    log_addition(by=author, what=group)
    return group


def update(group: CharacterGroup, author: Author, data: RawData) -> None:
    data = Validator(CHARACTER_GROUP).validated(data, update=True)

    if "name" in data:
        exist_group = CharacterGroup.get(name=data["name"])
        if exist_group and exist_group.id != group.id:
            raise ValidationError({"name": [lazy_gettext("Group already exists")]})

    changed_fields = set()
    for key, value in data.items():
        if getattr(group, key) != value:
            setattr(group, key, value)
            changed_fields |= {key}

    if changed_fields:
        log_changed_fields(by=author, what=group, fields=sorted(changed_fields))


def delete(group: CharacterGroup, author: Author) -> None:
    log_deletion(by=author, what=group)
    group.delete()
