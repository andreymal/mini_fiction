#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time

from pony import orm
from pony.orm import db_session

from flask_script import Manager
from mini_fiction import application

manager = Manager(application.create_app())


@manager.option('-f', '--fail-on-warn', dest='fail_on_warn', help='Return non-zero status code on warnings', action='store_true')
def status(fail_on_warn):
    from mini_fiction.utils import status as status_module
    orm.sql_debug(False)
    with db_session:
        fails, warns = status_module.print_all(manager.app)
        if fails or fail_on_warn and warns:
            sys.exit(1)


@manager.command
def shell():
    import code
    import mini_fiction
    from mini_fiction import models
    with db_session:
        code.interact(local={'mini_fiction': mini_fiction, 'app': manager.app, 'm': models})


@manager.option('-s', '--silent', dest='silent', help='Don\'t print progress bar to console', action='store_true')
def seed(silent=False):
    from mini_fiction import fixtures
    orm.sql_debug(False)
    fixtures.seed(progress=not silent, only_create=True)


@manager.command
def initsphinx():
    from mini_fiction.management.commands.initsphinx import initsphinx as cmd
    orm.sql_debug(False)
    cmd()


@manager.command
def sphinxconf():
    from mini_fiction.management.commands.sphinxconf import sphinxconf as cmd
    cmd()


@manager.command
def collectstatic():
    from mini_fiction.management.commands.collectstatic import collectstatic as cmd
    orm.sql_debug(False)
    with db_session:
        cmd()


@manager.command
def createsuperuser():
    from mini_fiction.management.commands.createsuperuser import createsuperuser as cmd
    orm.sql_debug(False)
    with db_session:
        cmd()


@manager.option('-e', '--eager', dest='eager', help='Don\'t use Celery for delayed sending', action='store_true')
@manager.option('recipients', metavar='recipients', nargs='+', default=(), help='Recipient addresses')
def sendtestemail(recipients, eager=False):
    from mini_fiction.management.commands.sendtestemail import sendtestemail as cmd
    orm.sql_debug(False)
    with db_session:
        cmd(recipients, eager)


@manager.command
def checkstorycomments():
    from mini_fiction.management.commands.checkcomments import checkstorycomments as cmd
    orm.sql_debug(False)
    cmd()


@manager.command
def checkstorylocalcomments():
    from mini_fiction.management.commands.checkcomments import checkstorylocalcomments as cmd
    orm.sql_debug(False)
    cmd()


@manager.command
def checknewscomments():
    from mini_fiction.management.commands.checkcomments import checknewscomments as cmd
    orm.sql_debug(False)
    cmd()


@manager.command
def checkwordscount():
    from mini_fiction.management.commands.checkwordscount import checkwordscount as cmd
    orm.sql_debug(False)
    cmd()


@manager.command
def checkstoryvoting():
    from mini_fiction.management.commands.checkstoryvoting import checkstoryvoting as cmd
    orm.sql_debug(False)
    cmd()


@manager.option('-s', '--silent', dest='silent', help='Don\'t print progress bar to console', action='store_true')
@manager.option('-c', '--compression', dest='gzip_compression', type=int, default=0, choices=list(range(10)), help='Use gzip compression for files')
@manager.option('entities_list', metavar='entity_name', nargs='*', default=(), help='Names of entities that will be dumped (lowercase, all by default)')
@manager.option('dirpath', metavar='output_directory', help='Directory where dump will be saved')
def dumpdb(dirpath, entities_list, gzip_compression=0, silent=False):
    from mini_fiction.dumpload import dumpdb_console as cmd
    orm.sql_debug(False)
    cmd(
        dirpath,
        entities_list if entities_list and 'all' not in entities_list else [],
        gzip_compression,
        progress=not silent,
    )


@manager.option('-s', '--silent', dest='silent', help='Don\'t print progress bar to console', action='store_true')
@manager.option('-C', '--only-create', dest='only_create', help='Only create non-existent objects', action='store_true')
@manager.option('pathlist', metavar='input_directory', nargs='+', help='Directories or files with dump data')
def loaddb(pathlist, silent=False, only_create=False):
    from mini_fiction.dumpload import loaddb_console as cmd
    orm.sql_debug(False)
    cmd(pathlist, progress=not silent, only_create=only_create)


@manager.option('-k', '--keep-broken', dest='keep_broken', help='Don\'t delete ZIP file if something goes wrong (useful for debugging)', action='store_true')
@manager.option('path', metavar='path/to/file.zip', help='ZIP file where dump will be saved')
def zip_dump(path, keep_broken=False):
    from mini_fiction.dumpload import zip_dump as cmd
    orm.sql_debug(False)
    path = os.path.abspath(path)

    tm = time.time()
    cmd(path, keep_broken=keep_broken)
    print('Done with {:.2f}s: {}'.format(time.time() - tm, path))


def run():
    manager.run()

if __name__ == "__main__":
    run()
