#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import db_session

from mini_fiction.management.manager import manager


@manager.command
def shell():
    import code
    import mini_fiction
    from mini_fiction import models
    with db_session:
        code.interact(local={'mini_fiction': mini_fiction, 'app': manager.app, 'm': models})
