#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import click
from pony import orm

from mini_fiction.management.manager import cli
from mini_fiction.utils.misc import timedelta_format


@cli.command()
@click.option('-s', '--silent', 'silent', help='Don\'t print progress bar to console', is_flag=True)
@click.option('-C', '--only-create', 'only_create', help='Only create non-existent objects', is_flag=True)
@click.argument('pathlist', nargs=-1, required=True)
def loaddb(pathlist, silent, only_create):
    from mini_fiction.dumpload import loaddb_console as cmd
    orm.sql_debug(False)
    tm = time.time()
    cmd(pathlist, verbosity=1 if silent else 2, only_create=only_create)
    print('Done in {}.'.format(timedelta_format(time.time() - tm)))
