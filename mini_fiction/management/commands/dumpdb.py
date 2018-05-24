#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import click
from pony import orm

from mini_fiction.management.manager import cli
from mini_fiction.utils.misc import timedelta_format


@cli.command(short_help='Makes a database dump.', help='Creates a jsonl dump of ENTITIES content (all by default) and saves it into DIRECTORY.')
@click.option('-s', '--silent', 'silent', help='Don\'t print progress bar to console.', is_flag=True)
@click.option('-c', '--compression', 'gzip_compression', type=click.IntRange(0, 9), default=0, help='Use gzip compression for files.')
@click.argument('dirpath', metavar='DIRECTORY')
@click.argument('entities_list', metavar='ENTITIES', nargs=-1)
def dumpdb(dirpath, entities_list, gzip_compression, silent):
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
