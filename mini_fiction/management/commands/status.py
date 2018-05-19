#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from pony import orm
from pony.orm import db_session

from mini_fiction.management.manager import manager


@manager.option('-f', '--fail-on-warn', dest='fail_on_warn', help='Return non-zero status code on warnings', action='store_true')
def status(fail_on_warn):
    from mini_fiction.utils import status as status_module
    orm.sql_debug(False)
    with db_session:
        fails, warns = status_module.print_all(manager.app)
        if fails or fail_on_warn and warns:
            sys.exit(1)
