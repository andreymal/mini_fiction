from dataclasses import dataclass
from enum import auto
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from flask import current_app

from mini_fiction.utils.enum import AutoName


class ImageKind(AutoName):
    CHARACTERS = auto()


@dataclass
class ImageMeta:
    relative_path: str
    sha256sum: str


def save_image(*, kind: ImageKind, data: bytes) -> ImageMeta:
    relative_path = Path(kind.value) / f'{uuid4()}.png'
    save_path = current_app.config['MEDIA_ROOT'] / relative_path

    save_path.parent.mkdir(parents=True)

    with save_path.open(mode='wb') as fp:
        fp.write(data)

    return ImageMeta(relative_path=relative_path.as_posix(), sha256sum=sha256(data).hexdigest())
