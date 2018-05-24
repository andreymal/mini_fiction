#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

import click
from pony import orm

from mini_fiction.management.manager import cli


@cli.command(short_help='Makes a dump of website config from DB.', help=(
    'Makes a zipped dump of some that are part of the configuration: '
    'logopic, charactergroup, character, category, classifier, rating, '
    'staticpage, htmlblock, adminlogtype and system user (without password). '
    'Stories, comments, news and other user content will not be added.'
))
@click.option('-k', '--keep-broken', 'keep_broken', help='Don\'t delete ZIP file if something goes wrong (useful for debugging).', is_flag=True)
@click.argument('path', 'path/to/destination.zip')
def zip_dump(path, keep_broken):
    from mini_fiction.dumpload import zip_dump as cmd
    orm.sql_debug(False)
    path = os.path.abspath(path)

    tm = time.time()
    cmd(path, keep_broken=keep_broken)
    print('Done with {:.2f}s: {}'.format(time.time() - tm, path))
