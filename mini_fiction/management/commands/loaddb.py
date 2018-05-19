#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

from pony import orm

from mini_fiction.management.manager import manager
from mini_fiction.utils.misc import timedelta_format


@manager.option('-s', '--silent', dest='silent', help='Don\'t print progress bar to console', action='store_true')
@manager.option('-C', '--only-create', dest='only_create', help='Only create non-existent objects', action='store_true')
@manager.option('pathlist', metavar='input_directory', nargs='+', help='Directories or files with dump data')
def loaddb(pathlist, silent=False, only_create=False):
    from mini_fiction.dumpload import loaddb_console as cmd
    orm.sql_debug(False)
    tm = time.time()
    cmd(pathlist, verbosity=1 if silent else 2, only_create=only_create)
    print('Done in {}.'.format(timedelta_format(time.time() - tm)))
