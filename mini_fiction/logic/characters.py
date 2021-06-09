from flask_babel import lazy_gettext

from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.logic.image import CharacterBundle, cleanup_image, save_image
from mini_fiction.models import Author, Character, CharacterGroup
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

    raw_data = data.pop("picture").stream.read()
    saved_image = save_image(bundle=CharacterBundle, raw_data=raw_data)
    if not saved_image:
        raise ValidationError({"picture": ["Cannot save image"]})

    character = Character(**data)
    character.image = saved_image
    character.flush()

    log_addition(by=author, what=character)

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

    if errors:
        raise ValidationError(errors)

    changed_fields = set()

    raw_picture = data.pop("picture", None)
    if raw_picture:
        old_saved_image = character.image
        raw_data = raw_picture.stream.read()
        saved_image = save_image(bundle=CharacterBundle, raw_data=raw_data)
        if not saved_image:
            raise ValidationError({"picture": ["Cannot save image"]})
        character.image = saved_image
        changed_fields |= {"image_bundle"}
        later(lambda: cleanup_image(old_saved_image))

    for key, value in data.items():
        if key == "group":
            if character.group.id != value:
                setattr(character, key, value)
                changed_fields |= {key}
        elif getattr(character, key) != value:
            setattr(character, key, value)
            changed_fields |= {key}

    if changed_fields:
        log_changed_fields(by=author, what=character, fields=sorted(changed_fields))


def delete(character: Character, author: Author) -> None:
    log_deletion(by=author, what=character)
    old_saved_image = character.image
    later(lambda: cleanup_image(old_saved_image))
    character.delete()
