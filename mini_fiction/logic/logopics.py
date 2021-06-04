import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import current_app

from mini_fiction.models import AdminLog, Author, Logopic
from mini_fiction.utils.image import ImageKind, save_image
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import RawData, Validator
from mini_fiction.validation.logopics import LOGOPIC, LOGOPIC_FOR_UPDATE


@dataclass
class PreparedLogopic:
    url: str
    original_link: str
    original_link_label: Dict[str, str]


def create(author: Author, data: RawData) -> Logopic:
    data = Validator(LOGOPIC).validated(data)

    picture = data.pop("picture").stream.read()
    picture_metadata = save_image(
        kind=ImageKind.LOGOPICS, data=picture, extension="jpg"
    )

    logopic = Logopic(
        picture=picture_metadata.relative_path,
        sha256sum=picture_metadata.sha256sum,
        **data
    )
    logopic.flush()

    current_app.cache.delete("logopics")
    AdminLog.bl.create(user=author, obj=logopic, action=AdminLog.ADDITION)
    return logopic


def update(logopic: Logopic, author: Author, data: RawData) -> Logopic:
    data = Validator(LOGOPIC_FOR_UPDATE).validated(data, update=True)

    changed_fields = set()

    old_path: Optional[Path] = None

    for key, value in data.items():
        if key == "picture":
            if value:
                picture = value.stream.read()
                old_path = logopic.picture_path
                picture_metadata = save_image(
                    kind=ImageKind.LOGOPICS, data=picture, extension="jpg"
                )
                logopic.picture = picture_metadata.relative_path
                logopic.sha256sum = picture_metadata.sha256sum
                changed_fields |= {
                    "picture",
                }
        else:
            if getattr(logopic, key) != value:
                setattr(logopic, key, value)
                changed_fields |= {
                    key,
                }

    if changed_fields:
        logopic.updated_at = datetime.utcnow()
        current_app.cache.delete("logopics")

        AdminLog.bl.create(
            user=author,
            obj=logopic,
            action=AdminLog.CHANGE,
            fields=sorted(changed_fields),
        )

    if old_path and old_path.exists():
        later(lambda: old_path.unlink())
    return logopic


def delete(logopic: Logopic, author: Author) -> None:
    AdminLog.bl.create(user=author, obj=logopic, action=AdminLog.DELETION)
    old_path = logopic.picture_path
    if old_path and old_path.exists():
        later(lambda: old_path.unlink())
    logopic.delete()
    current_app.cache.delete("logopics")


def get_all() -> List[PreparedLogopic]:
    result = current_app.cache.get("logopics")
    if result is not None:
        return result

    result = []
    for lp in Logopic.select(lambda x: x.visible):

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
                url=lp.url,
                original_link=lp.original_link,
                original_link_label=original_link_label,
            )
        )

    current_app.cache.set("logopics", result, 7200)
    return result


def get_current() -> Optional[PreparedLogopic]:
    logos = get_all()
    if not logos:
        return None
    return random.Random(int(time.time()) // 3600).choice(logos)
