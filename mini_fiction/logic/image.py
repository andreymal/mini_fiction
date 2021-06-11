from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Set, Type, Union
from uuid import uuid4

from flask import current_app
from PIL.Image import LANCZOS, Image, UnidentifiedImageError
from PIL.Image import open as open_image
from pydantic import BaseModel  # pylint: disable=no-name-in-module
from typing_extensions import ClassVar, Literal

IMAGE_QUALITY = 85  # It's enough


class ResizedContainer(BaseModel):
    webp: bytes
    png: bytes
    jpeg: bytes
    width: int
    height: int


class ImageMeta(BaseModel):
    webp: str
    png: str
    jpeg: str
    width: int
    height: int


class AvatarBundle(BaseModel):
    x32: ImageMeta
    x48: ImageMeta
    x64: ImageMeta
    x128: ImageMeta

    kind: Literal["avatars"] = "avatars"
    # NOTE: https://github.com/samuelcolvin/pydantic/pull/2336 here and below
    _kind: ClassVar[str] = "avatars"


class CharacterBundle(BaseModel):
    x32: ImageMeta

    kind: Literal["characters"] = "characters"
    _kind: ClassVar[str] = "characters"


class LogopicBundle(BaseModel):
    x1194: ImageMeta

    kind: Literal["logopics"] = "logopics"
    _kind: ClassVar[str] = "logopics"


ImageBundle = Union[AvatarBundle, CharacterBundle, LogopicBundle]

SQUARE_IMAGES = frozenset((AvatarBundle, CharacterBundle))


class SavedImage(BaseModel):
    resized: ImageBundle
    original: str


def _extract_width_dimension(*, bundle: Type[ImageBundle]) -> Set[int]:
    return {
        int(name.strip("x"))
        for name in bundle.__fields__.keys()
        if name.startswith("x")
    }


def _resize_image(
    *,
    image: Image,
    desired_width: int,
    desired_height: Optional[int],
) -> ResizedContainer:
    if desired_height is None:
        # Proportional resize
        (actual_width, actual_height) = image.size
        ratio = actual_width / desired_width
        desired_height = int(actual_height / ratio)

    webp_buffer = BytesIO()
    png_buffer = BytesIO()
    jpeg_buffer = BytesIO()
    with image.resize((desired_width, desired_height), resample=LANCZOS) as resized:
        resized.convert("RGBA").save(webp_buffer, format="WEBP", quality=IMAGE_QUALITY)
        resized.convert("RGBA").save(png_buffer, format="PNG", quality=IMAGE_QUALITY)
        resized.convert("RGB").save(jpeg_buffer, format="JPEG", quality=IMAGE_QUALITY)

    return ResizedContainer(
        webp=webp_buffer.getvalue(),
        png=png_buffer.getvalue(),
        jpeg=png_buffer.getvalue(),
        width=desired_width,
        height=desired_height,
    )


def _save_resized_image(
    *,
    relative_path: Path,
    bundle: Type[ImageBundle],
    image: Image,
) -> ImageBundle:
    media_root: Path = current_app.config["MEDIA_ROOT"]
    dimensions = {
        (width, (width if bundle in SQUARE_IMAGES else None))
        for width in _extract_width_dimension(bundle=bundle)
    }

    kw: Dict[str, ImageMeta] = {}
    for width, height in dimensions:
        result = _resize_image(image=image, desired_width=width, desired_height=height)
        webp_path = relative_path.with_suffix(f".{width}.webp")
        png_path = relative_path.with_suffix(f".{width}.png")
        jpeg_path = relative_path.with_suffix(f".{width}.jpeg")

        (media_root / webp_path).write_bytes(result.webp)
        # Maybe, someday, we will remove this fallback
        (media_root / png_path).write_bytes(result.png)

        kw[f"x{width}"] = ImageMeta(
            webp=webp_path.as_posix(),
            png=png_path.as_posix(),
            jpeg=jpeg_path.as_posix(),
            width=result.width,
            height=result.height,
        )
    # Despite being unsafe hack there are strict type guarantees in signature, so let it be
    return bundle(**kw)  # type: ignore


def _save_original_image(
    *, relative_path: Path, raw_data: bytes, extension: str
) -> str:
    media_root: Path = current_app.config["MEDIA_ROOT"]
    save_path = relative_path.with_suffix(f".orig.{extension}")
    (media_root / save_path).write_bytes(raw_data)
    return save_path.as_posix()


def _validate_image(raw_data: bytes) -> Optional[Image]:
    try:
        image: Image = open_image(BytesIO(raw_data))
        image.load()
        return image
    except UnidentifiedImageError:
        return None


def save_image(
    *,
    bundle: Type[ImageBundle],
    raw_data: bytes,
) -> Optional[SavedImage]:
    image = _validate_image(raw_data=raw_data)
    if not image:
        return None

    name = uuid4().hex
    relative_path = (
        Path(bundle._kind) / name[:2] / name  # pylint: disable=protected-access
    )

    media_root: Path = current_app.config["MEDIA_ROOT"]
    (media_root / relative_path).parent.mkdir(parents=True, exist_ok=True)

    original = _save_original_image(
        relative_path=relative_path,
        raw_data=raw_data,
        extension=image.format.lower(),  # noqa: FS002
    )
    resized = _save_resized_image(
        relative_path=relative_path, bundle=bundle, image=image
    )

    return SavedImage(original=original, resized=resized)


def cleanup_image(saved_image: SavedImage) -> None:
    if saved_image is None:
        return

    media_root: Path = current_app.config["MEDIA_ROOT"]

    for name, meta in saved_image.resized:
        if name.startswith("x"):
            webp_file = media_root / meta.webp
            if webp_file.exists():
                webp_file.unlink()
            png_file = media_root / meta.png
            if png_file.exists():
                png_file.unlink()

    original_path = media_root / saved_image.original
    if original_path.exists():
        original_path.unlink()
