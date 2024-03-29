from __future__ import annotations

import re
from itertools import chain
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import g, url_for
from pydantic import BaseModel, parse_file_as
from werkzeug.datastructures import MultiDict

from mini_fiction.logic.environment import get_settings
from mini_fiction.settings import FaviconBundle

PLAIN_STYLESHEET = re.compile(r".*\.css$")
PLAIN_SCRIPT = re.compile(r".*\.js$")
ENTRYPOINT_SCRIPT = re.compile(r"index.*\.js$")


class Asset(BaseModel):
    src: str
    integrity: str


class ResolvedAsset(BaseModel):
    url: str
    integrity: str


RawAsset = Dict[str, Asset]
ResolvedAssets = List[Tuple[str, ResolvedAsset]]


def get_manifest(*, bundle_type: str, path: Path) -> ResolvedAssets:
    bundle_dir_name = path.parent.name

    if not path.exists():
        raise FileNotFoundError(
            f"Manifest file {path.as_posix()} does not exist. "
            'Use "make frontend" or "make frontend-build" command to create it'
        )

    raw_assets: RawAsset = parse_file_as(RawAsset, path)
    return [
        (
            name,
            ResolvedAsset(
                url=url_for(bundle_type, filename=f"{bundle_dir_name}/{raw_asset.src}"),
                integrity=raw_asset.integrity,
            ),
        )
        for name, raw_asset in raw_assets.items()
    ]


# pylint: disable=unsubscriptable-object
def _get_assets() -> MultiDict[str, ResolvedAsset]:
    static_root = Path(get_settings().STATIC_ROOT)
    bundled_manifests = chain(
        *(
            get_manifest(bundle_type="static", path=manifest_path)
            for manifest_path in static_root.glob("*/manifest.json")
        )
    )
    localstatic_root_path = get_settings().LOCALSTATIC_ROOT
    if localstatic_root_path is not None:
        localstatic_root = Path(localstatic_root_path)
        localstatic_manifests = chain(
            *(
                get_manifest(bundle_type="localstatic", path=manifest_path)
                for manifest_path in localstatic_root.glob("*/manifest.json")
            )
        )
    else:
        localstatic_manifests = chain()

    return MultiDict((*bundled_manifests, *localstatic_manifests))


# pylint: disable=unsubscriptable-object
def get_assets() -> MultiDict[str, ResolvedAsset]:
    if get_settings().FRONTEND_MANIFESTS_AUTO_RELOAD:
        # Always serve assets from fresh manifests
        return _get_assets()

    manifests = getattr(g, "frontend_assets", None)
    if manifests is None:
        # Load and cache manifests
        manifests = _get_assets()
        setattr(g, "frontend_assets", manifests)
    return manifests


def stylesheets() -> List[ResolvedAsset]:
    return [
        asset
        for name, asset in get_assets().items(True)
        if PLAIN_STYLESHEET.match(name)
    ]


def scripts(*, entrypoint: bool = False) -> List[ResolvedAsset]:
    return [
        asset
        for name, asset in get_assets().items(True)
        if (entrypoint and ENTRYPOINT_SCRIPT or PLAIN_SCRIPT).match(name)
    ]


def favicon_bundle() -> FaviconBundle:
    config_favicons: Optional[FaviconBundle] = get_settings().FAVICONS
    if config_favicons is not None:
        return config_favicons

    assets = get_assets()
    legacy_favicon = assets.get("favicon.ico")
    main_favicon = assets.get("favicon.png")
    apple_favicon = assets.get("apple-touch-icon.png")

    return FaviconBundle(
        legacy=legacy_favicon and legacy_favicon.url or None,
        main=main_favicon and main_favicon.url or None,
        apple=apple_favicon and apple_favicon.url or None,
    )
