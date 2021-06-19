import re
from itertools import chain
from pathlib import Path
from typing import Dict, List, Tuple

from flask import current_app, g, url_for
from pydantic import BaseModel, parse_file_as  # pylint: disable=no-name-in-module

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


def _get_assets() -> ResolvedAssets:
    static_root = Path(current_app.config["STATIC_ROOT"])
    bundled_manifests = chain(
        *(
            get_manifest(bundle_type="static", path=manifest_path)
            for manifest_path in static_root.glob("*/manifest.json")
        )
    )
    if current_app.config["LOCALSTATIC_ROOT"] is not None:
        localstatic_root = Path(current_app.config["LOCALSTATIC_ROOT"])
        localstatic_manifests = chain(
            *(
                get_manifest(bundle_type="localstatic", path=manifest_path)
                for manifest_path in localstatic_root.glob("*/manifest.json")
            )
        )
    else:
        localstatic_manifests = chain()

    return [*bundled_manifests, *localstatic_manifests]


def get_assets() -> List[Tuple[str, ResolvedAsset]]:
    if current_app.config["FRONTEND_MANIFESTS_AUTO_RELOAD"]:
        # Always serve assets from fresh manifests
        return _get_assets()

    manifests = getattr(g, "frontend_assets", None)
    if manifests is None:
        # Load and cache manifests
        manifests = _get_assets()
        setattr(g, "frontend_assets", manifests)
    return manifests


def stylesheets() -> List[ResolvedAsset]:
    return [asset for name, asset in get_assets() if PLAIN_STYLESHEET.match(name)]


def scripts(*, entrypoint: bool = False) -> List[ResolvedAsset]:
    return [
        asset
        for name, asset in get_assets()
        if (entrypoint and ENTRYPOINT_SCRIPT or PLAIN_SCRIPT).match(name)
    ]
