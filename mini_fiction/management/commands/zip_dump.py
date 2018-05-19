#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

from pony import orm

from mini_fiction.management.manager import manager


@manager.option('-k', '--keep-broken', dest='keep_broken', help='Don\'t delete ZIP file if something goes wrong (useful for debugging)', action='store_true')
@manager.option('path', metavar='path/to/file.zip', help='ZIP file where dump will be saved')
def zip_dump(path, keep_broken=False):
    from mini_fiction.dumpload import zip_dump as cmd
    orm.sql_debug(False)
    path = os.path.abspath(path)

    tm = time.time()
    cmd(path, keep_broken=keep_broken)
    print('Done with {:.2f}s: {}'.format(time.time() - tm, path))
