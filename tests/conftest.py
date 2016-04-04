#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import pytest
from pony.orm import db_session

from mini_fiction import database, fixtures
from mini_fiction.application import create_app


flask_app = None


@pytest.fixture(scope="session", autouse=True)
def app():
    global flask_app
    flask_app = create_app()
    if not flask_app.config['TESTING']:
        raise RuntimeError('This is not testing configuration')

    with db_session:
        # Init testing database
        fixtures.seed()

    return flask_app


@pytest.fixture
def selenium(selenium):
    selenium.implicitly_wait(5)
    return selenium


@pytest.fixture(scope="session")
def factories():
    import factories as factories_module
    return factories_module


@pytest.fixture
def wait_ajax(selenium):
    def wait():
        i = 0
        while i < 20 and selenium.execute_script('return window.core && window.core.state.current !== null;'):
            time.sleep(0.15)
            i += 1
    return wait


@pytest.yield_fixture(scope="function", autouse=True)
def database_cleaner():
    assert flask_app.config['DATABASE_CLEANER']['provider'] in ('sqlite3',)
    try:
        with db_session:
            yield
    finally:
        database.db.rollback()

        # Workaround for live_server
        conn = database.db.provider.pool.con
        conn.execute('PRAGMA foreign_keys = OFF')
        conn.execute('BEGIN TRANSACTION')
        for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            if x[0].lower() in ('htmlblock', 'rating', 'staticpage'):
                continue  # fixtures
            conn.execute('DELETE FROM {}'.format(x[0]))
        conn.execute('COMMIT')
        database.db.disconnect()
