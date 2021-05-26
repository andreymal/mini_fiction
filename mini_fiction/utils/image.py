from dataclasses import dataclass
from enum import auto
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from flask import current_app

from mini_fiction.utils.enum import AutoName


class ImageKind(AutoName):
    CHARACTERS = auto()
    LOGOPICS = auto()
    ILLUSTRATIONS = auto()
    COMMON = auto()


@dataclass
class ImageMeta:
    relative_path: str
    sha256sum: str


# FIXME: Detect extension with libmagic1 (see python-magic)
def save_image(*, kind: ImageKind, data: bytes, extension: str) -> ImageMeta:
    name = uuid4().hex
    relative_path = Path(kind.value) / name[:2] / f'{name}.{extension}'
    save_path = current_app.config['MEDIA_ROOT'] / relative_path

    save_path.parent.mkdir(parents=True)

    with save_path.open(mode='wb') as fp:
        fp.write(data)

    return ImageMeta(relative_path=relative_path.as_posix(), sha256sum=sha256(data).hexdigest())
