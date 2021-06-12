import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.logic.caching import get_cache
from mini_fiction.logic.image import LogopicBundle, cleanup_image, save_image
from mini_fiction.models import Author, Logopic
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.logopics import LOGOPIC, LOGOPIC_FOR_UPDATE


@dataclass
class PreparedLogopic:
    bundle: LogopicBundle
    original_link: str
    original_link_label: Dict[str, str]


def create(author: Author, data: RawData) -> Logopic:
    data = Validator(LOGOPIC).validated(data)

    raw_data = data.pop("picture").stream.read()
    saved_image = save_image(bundle=LogopicBundle, raw_data=raw_data)
    if not saved_image:
        raise ValidationError({"picture": ["Cannot save image"]})

    logopic = Logopic(**data)
    logopic.image = saved_image
    logopic.flush()

    get_cache().delete("logopics")
    log_addition(by=author, what=logopic)
    return logopic


def update(logopic: Logopic, author: Author, data: RawData) -> Logopic:
    data = Validator(LOGOPIC_FOR_UPDATE).validated(data, update=True)

    changed_fields = set()

    raw_picture = data.pop("picture", None)
    if raw_picture:
        old_saved_image = logopic.image
        raw_data = raw_picture.stream.read()
        saved_image = save_image(bundle=LogopicBundle, raw_data=raw_data)
        if not saved_image:
            raise ValidationError({"picture": ["Cannot save image"]})
        logopic.image = saved_image
        changed_fields |= {"image_bundle"}
        later(lambda: cleanup_image(old_saved_image))

    for key, value in data.items():
        if getattr(logopic, key) != value:
            setattr(logopic, key, value)
            changed_fields |= {key}

    if changed_fields:
        logopic.updated_at = datetime.utcnow()
        get_cache().delete("logopics")

        log_changed_fields(by=author, what=logopic, fields=sorted(changed_fields))

    return logopic


def delete(logopic: Logopic, author: Author) -> None:
    log_deletion(by=author, what=logopic)
    old_saved_image = logopic.image
    later(lambda: cleanup_image(old_saved_image))
    logopic.delete()
    get_cache().delete("logopics")


def get_all() -> List[PreparedLogopic]:
    result = get_cache().get("logopics")
    if result is not None:
        return result

    result = []
    for lp in Logopic.select(lambda x: x.visible):  # type: Logopic

        original_link_label = {"": ""}
        for line in lp.original_link_label.split("\n"):
            line = line.strip()
            if not line:
                continue
            if 0 <= line.find("=") <= 4:
                lang, line = line.split("=", 1)
                original_link_label[lang] = line.strip()
            else:
                original_link_label[""] = line
        result.append(
            PreparedLogopic(
                bundle=lp.bundle,
                original_link=lp.original_link,
                original_link_label=original_link_label,
            )
        )

    get_cache().set("logopics", result, 7200)
    return result


def get_current() -> Optional[PreparedLogopic]:
    logos = get_all()
    if not logos:
        return None
    return random.Random(int(time.time()) // 3600).choice(logos)
