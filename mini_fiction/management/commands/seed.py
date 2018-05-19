#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm

from mini_fiction.management.manager import manager


@manager.option('-s', '--silent', dest='silent', help='Don\'t print progress bar to console', action='store_true')
def seed(silent=False):
    from mini_fiction import fixtures
    orm.sql_debug(False)
    fixtures.seed(verbosity=1 if silent else 2, only_create=True)
