#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from pony import orm

from mini_fiction.management.manager import cli


@cli.command(help='Loads default fixtures into the database.')
@click.option('-O', '--overwrite', 'overwrite', help='Overwrite existing objects', is_flag=True)
@click.option("-v", "--verbose", "verbosity", count=True, help='Verbosity: -v prints status, -vv prints progress bar.')
def seed(verbosity=0, overwrite=False):
    from mini_fiction import fixtures
    orm.sql_debug(False)
    fixtures.seed(verbosity=verbosity, only_create=not overwrite)
