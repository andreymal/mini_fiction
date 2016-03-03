#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from pony.orm import Database


db = Database()


def configure_for_app(app):
    db.bind(
        app.config['DATABASE_ENGINE'],
        **app.config['DATABASE']
    )
    db.generate_mapping(create_tables=True)
    if app.config['SQL_DEBUG']:
        orm.sql_debug(True)
