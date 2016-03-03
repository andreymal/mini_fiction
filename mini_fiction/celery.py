#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file should be executed only by celery worker

from mini_fiction.application import create_app

flask_app = create_app()
celery = flask_app.celery  # pylint: disable=no-member
