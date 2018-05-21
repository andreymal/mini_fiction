#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import click

from pony import orm
from pony.orm import db_session
from flask import current_app

from mini_fiction.management.manager import cli


@cli.command()
@click.option('-f', '--fail-on-warn', 'fail_on_warn', help='Return non-zero status code on warnings', is_flag=True)
def status(fail_on_warn):
    from mini_fiction.utils import status as status_module
    orm.sql_debug(False)
    with db_session:
        fails, warns = status_module.print_all(current_app)
        if fails or fail_on_warn and warns:
            sys.exit(1)
