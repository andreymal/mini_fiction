#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app
from pony.orm import db_session

from mini_fiction.management.manager import cli


@cli.command(help='Runs a Python interactive interpreter.')
def shell():
    import code
    import mini_fiction
    from mini_fiction import models
    with db_session:
        code.interact(local={
            'mini_fiction': mini_fiction,
            'app': current_app._get_current_object(),
            'm': models,
        })
