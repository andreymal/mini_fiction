from pathlib import Path
from typing import Any, Optional

from flask_babel import lazy_gettext

from mini_fiction.models import AdminLog, Author, Character, CharacterGroup
from mini_fiction.utils.image import ImageKind, save_image
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.sorting import CHARACTER, CHARACTER_FOR_UPDATE


def create(author: Author, data: RawData) -> Character:
    data = Validator(CHARACTER).validated(data)

    errors = {}

    exist_character = Character.get(name=data["name"])
    if exist_character:
        errors["name"] = [lazy_gettext("Character already exists")]

    group = CharacterGroup.get(id=data["group"])
    if not group:
        errors["group"] = [lazy_gettext("Group not found")]

    if errors:
        raise ValidationError(errors)

    picture = validate_and_get_picture_data(data.pop("picture"))
    picture_metadata = save_image(
        kind=ImageKind.CHARACTERS, data=picture, extension="png"
    )

    character = Character(
        picture=picture_metadata.relative_path,
        sha256sum=picture_metadata.sha256sum,
        **data
    )
    character.flush()

    AdminLog.bl.create(user=author, obj=character, action=AdminLog.ADDITION)

    return character


def update(character: Character, author: Author, data: RawData) -> None:
    data = Validator(CHARACTER_FOR_UPDATE).validated(data, update=True)

    errors = {}

    if "name" in data:
        exist_character = Character.get(name=data["name"])
        if exist_character and exist_character.id != character.id:
            errors["name"] = [lazy_gettext("Character already exists")]

    if "group" in data:
        group = CharacterGroup.get(id=data["group"])
        if not group:
            errors["group"] = [lazy_gettext("Group not found")]
    else:
        group = None

    if errors:
        raise ValidationError(errors)

    changed_fields = set()

    old_path: Optional[Path] = None

    if data.get("picture"):
        picture = validate_and_get_picture_data(data["picture"])
    else:
        picture = None

    for key, value in data.items():
        if key == "picture":
            if picture is not None:
                old_path = character.picture_path
                picture_metadata = save_image(
                    kind=ImageKind.CHARACTERS, data=picture, extension="jpg"
                )
                character.picture = picture_metadata.relative_path
                character.sha256sum = picture_metadata.sha256sum
                changed_fields |= {"picture"}
                if old_path and old_path.exists():
                    later(
                        lambda: old_path.unlink()  # pylint: disable=unnecessary-lambda
                    )
        elif key == "group":
            if character.group.id != value:
                setattr(character, key, value)
                changed_fields |= {key}
        elif getattr(character, key) != value:
            setattr(character, key, value)
            changed_fields |= {key}

    if changed_fields:
        AdminLog.bl.create(
            user=author,
            obj=character,
            action=AdminLog.CHANGE,
            fields=sorted(changed_fields),
        )


def delete(character: Character, author: Author) -> None:
    AdminLog.bl.create(user=author, obj=character, action=AdminLog.DELETION)
    old_path = character.picture_path
    if old_path and old_path.exists():
        later(lambda: old_path.unlink())  # pylint: disable=unnecessary-lambda
    character.delete()


# FIXME: Decouple validation logic and move it to mini_fiction.utils.image # pylint: disable=fixme
def validate_and_get_picture_data(picture: Any) -> Any:
    fp = picture.stream
    header = fp.read(4)
    if header != b"\x89PNG":
        raise ValidationError({"picture": [lazy_gettext("PNG only")]})
    data = header + fp.read(16384 - 4 + 1)  # 16 KiB + 1 byte for validation
    if len(data) > 16384:
        raise ValidationError(
            {
                "picture": [
                    lazy_gettext("Maximum picture size is {maxsize} KiB").format(
                        maxsize=16
                    )
                ]
            }
        )
    return data
