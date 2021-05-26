import os
from dataclasses import dataclass
from typing import Dict, Iterable

from flask import current_app, g
from flask import json as flask_json


@dataclass
class Asset:
    src: str
    integrity: str


@dataclass
class Manifest:
    size: int
    mtime: float
    assets: Dict[str, Asset]


def get_manifest() -> Manifest:
    manifest_path = current_app.config['FRONTEND_MANIFEST_PATH']

    manifest = getattr(g, 'webpack_manifest', None)
    if manifest is not None and current_app.config['FRONTEND_MANIFEST_AUTO_RELOAD']:
        # check if the manifest needs to be reloaded
        try:
            st = os.stat(manifest_path)
        except OSError:
            st = None
        if st is None or manifest.size != st.st_size or manifest.mtime != st.st_mtime:
            manifest = None

    if manifest is None:
        try:
            with open(manifest_path, encoding='utf-8-sig') as f:
                assets = {k: Asset(**v) for k, v in flask_json.load(f).items()}
            st = os.stat(manifest_path)

        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Manifest file {manifest_path} does not exist. "
                "Use 'make frontend' or 'make frontend-build' command to create it"
            ) from exc

        manifest = Manifest(
            size=st.st_size,
            mtime=st.st_mtime,
            assets=assets,
        )
        g.webpack_manifest = manifest

    return manifest


def webpack_asset(name: str) -> Asset:
    return get_manifest().assets[name]


def webpack_scripts() -> Iterable[Asset]:
    return [asset for name, asset in get_manifest().assets.items() if name.endswith('.js')]
