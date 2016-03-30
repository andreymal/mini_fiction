#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

from flask import url_for

from mini_fiction.database import db


def test_selenium_stub(app, client, selenium, live_server, factories):
    author = factories.AuthorFactory()
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    assert True
