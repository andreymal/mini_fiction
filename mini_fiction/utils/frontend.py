#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from collections import namedtuple

from flask import current_app, g
from flask import json as flask_json


Manifest = namedtuple('Manifest', ['size', 'mtime', 'assets'])
Asset = namedtuple('Asset', ['src', 'integrity'])


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
