#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from mini_fiction.settings import Development


class Local(Development):
    DATABASE_ENGINE = 'mysql'
    DATABASE = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'fanfics',
        'passwd': 'fanfics',
        'db': 'fanfics',
    }

    # LOGGER_LEVEL = logging.DEBUG

    # ADMINS = ['admin@example.org']
    # ERROR_EMAIL_FROM = 'minifiction@example.org'

    EMAIL_PORT = 1025
    DEFAULT_FROM_EMAIL = 'minifiction@andreymal.org'

    RECAPTCHA_PUBLIC_KEY = '...'
    RECAPTCHA_PRIVATE_KEY = '...'

    CELERY_ALWAYS_EAGER = False
    SPHINX_DISABLED = False

    # REGISTRATION_OPEN = False
    CHECK_PASSWORDS_SECURITY = True

    # SPHINX_CONFIG = dict(Development.SPHINX_CONFIG)
    # SPHINX_CONFIG['connection_params'] = {'host': '127.0.0.1', 'port': 9306, 'charset': 'utf8'}
