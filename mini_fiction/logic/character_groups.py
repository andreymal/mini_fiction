from flask_babel import lazy_gettext

from mini_fiction.models import AdminLog, Author, CharacterGroup
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.sorting import CHARACTER_GROUP


def create(author: Author, data: RawData) -> CharacterGroup:
    data = Validator(CHARACTER_GROUP).validated(data)

    exist_group = CharacterGroup.get(name=data["name"])
    if exist_group:
        raise ValidationError({"name": [lazy_gettext("Group already exists")]})

    group = CharacterGroup(**data)
    group.flush()
    AdminLog.bl.create(user=author, obj=group, action=AdminLog.ADDITION)
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
        AdminLog.bl.create(
            user=author,
            obj=group,
            action=AdminLog.CHANGE,
            fields=sorted(changed_fields),
        )


def delete(group: CharacterGroup, author: Author) -> None:
    AdminLog.bl.create(user=author, obj=group, action=AdminLog.DELETION)
    group.delete()
