#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import click
from pony import orm

from mini_fiction.management.manager import cli
from mini_fiction.utils.misc import timedelta_format


@cli.command(short_help='Loads json dump to the database.', help=(
    'Reads the jsonl dump from PATHLIST (directories or jsonl files) that '
    'was created by "loaddb" command and inserts it to the database.\n\n'
    'Please note that it can be slow; if you want to move big data between '
    'compatible databases native tools can be better (e.g. mysqldump '
    'for MySQL).'
))
@click.option('-s', '--silent', 'silent', help='Don\'t print progress bar to console.', is_flag=True)
@click.option('-C', '--only-create', 'only_create', help='Only create non-existent objects.', is_flag=True)
@click.argument('pathlist', nargs=-1, required=True)
def loaddb(pathlist, silent, only_create):
    from mini_fiction.dumpload import loaddb_console as cmd
    orm.sql_debug(False)
    tm = time.time()
    cmd(pathlist, verbosity=1 if silent else 2, only_create=only_create)
    print('Done in {}.'.format(timedelta_format(time.time() - tm)))
