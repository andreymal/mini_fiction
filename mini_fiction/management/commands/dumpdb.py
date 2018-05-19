#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

from pony import orm

from mini_fiction.management.manager import manager
from mini_fiction.utils.misc import timedelta_format


@manager.option('-s', '--silent', dest='silent', help='Don\'t print progress bar to console', action='store_true')
@manager.option('-c', '--compression', dest='gzip_compression', type=int, default=0, choices=list(range(10)), help='Use gzip compression for files')
@manager.option('entities_list', metavar='entity_name', nargs='*', default=(), help='Names of entities that will be dumped (lowercase, all by default)')
@manager.option('dirpath', metavar='output_directory', help='Directory where dump will be saved')
def dumpdb(dirpath, entities_list, gzip_compression=0, silent=False):
    from mini_fiction.dumpload import dumpdb_console as cmd
    orm.sql_debug(False)
    tm = time.time()
    cmd(
        dirpath,
        entities_list if entities_list and 'all' not in entities_list else [],
        gzip_compression,
        verbosity=1 if silent else 2,
    )
    print('Done in {}.'.format(timedelta_format(time.time() - tm)))
