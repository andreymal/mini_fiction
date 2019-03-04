#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import shutil

import pytest
from pony.orm import db_session

from mini_fiction import database, fixtures
from mini_fiction.application import create_app

# pylint: disable=W0621

flask_app = None


@pytest.yield_fixture(scope="session", autouse=True)
def app():
    global flask_app
    os.environ.setdefault('FLASK_ENV', 'test')
    flask_app = create_app()
    if not flask_app.config['TESTING']:
        raise RuntimeError('This is not testing configuration')

    with db_session:
        # Init testing database
        fixtures.seed(verbosity=0)

    yield flask_app

    shutil.rmtree(flask_app.config['TESTING_DIRECTORY'])


@pytest.fixture
def selenium(selenium):
    selenium.implicitly_wait(5)
    return selenium


@pytest.fixture
def chrome_options(chrome_options):
    chrome_options.add_argument('--no-sandbox')
    if flask_app.config.get('SELENIUM_HEADLESS'):
        chrome_options.add_argument('--headless')
    return chrome_options


@pytest.fixture
def firefox_options(firefox_options):
    if flask_app.config.get('SELENIUM_HEADLESS'):
        firefox_options.add_argument('-headless')
    return firefox_options


@pytest.fixture(scope="session")
def factories():
    import factories as factories_module
    return factories_module


@pytest.fixture
def testdir():
    return flask_app.config['TESTING_DIRECTORY']


@pytest.fixture
def wait_ajax(selenium):
    def wait():
        i = 0
        while i < 20 and selenium.execute_script('return window.amajaxify && window.amajaxify.state.current !== null;'):
            time.sleep(0.15)
            i += 1
    return wait


@pytest.yield_fixture(scope="function", autouse=True)
def database_cleaner(request):
    from mini_fiction.models import AdminLog

    if 'nodbcleaner' in request.keywords:
        yield
        return

    assert flask_app.config['DATABASE_CLEANER']['provider'] in ('sqlite3',)
    try:
        with db_session:  # FIXME: документация Pony ORM не советует так делать
            AdminLog.bl._load_type_cache()
            yield
    finally:
        database.db.rollback()

        # Workaround for live_server
        conn = database.db.provider.pool.con
        if conn:
            conn.execute('PRAGMA foreign_keys = OFF')
            conn.execute('BEGIN TRANSACTION')
            for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                if x[0].lower() in ('htmlblock', 'rating', 'staticpage'):
                    pass  # fixtures
                elif x[0].lower() == 'author':
                    conn.execute('DELETE FROM {} WHERE id != {}'.format(x[0], flask_app.config['SYSTEM_USER_ID']))
                else:
                    conn.execute('DELETE FROM {}'.format(x[0]))
            conn.execute('COMMIT')
            database.db.disconnect()
