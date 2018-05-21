#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from pony import orm

from mini_fiction.management.manager import cli


@cli.command()
@click.option('-s', '--silent', 'silent', help='Don\'t print progress bar to console', is_flag=True)
def seed(silent):
    from mini_fiction import fixtures
    orm.sql_debug(False)
    fixtures.seed(verbosity=1 if silent else 2, only_create=True)
