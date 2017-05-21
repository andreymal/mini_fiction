#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from mini_fiction.settings import Development


class Local(Development):
    # DATABASE_ENGINE = 'mysql'
    # DATABASE = {
    #     'host': '127.0.0.1',
    #     'port': 3306,
    #     'user': 'fanfics',
    #     'passwd': 'fanfics',
    #     'db': 'fanfics',
    # }

    # SERVER_NAME = 'example.org'
    # PREFERRED_URL_SCHEME = 'http'

    # LOGGER_LEVEL = logging.DEBUG

    # ADMINS = ['admin@example.org']
    # ERROR_EMAIL_HANDLER_PARAMS = {'mailhost': ('127.0.0.1', 1025)}
    ERROR_EMAIL_FROM = 'minifiction@example.org'

    # EMAIL_HOST = '127.0.0.1'
    # EMAIL_PORT = 1025
    DEFAULT_FROM_EMAIL = 'minifiction@example.org'

    # RECAPTCHA_PUBLIC_KEY = '...'
    # RECAPTCHA_PRIVATE_KEY = '...'
    # NOCAPTCHA = False

    # CELERY_CONFIG = dict(Config.CELERY_CONFIG)
    # CELERY_CONFIG['task_always_eager'] = False
    # SPHINX_DISABLED = False

    # REGISTRATION_OPEN = False
    CHECK_PASSWORDS_SECURITY = True

    DEBUG_TB_ENABLED = True

    # PROXIES_COUNT = 1  # uncomment it if you use nginx as frontend
    # SECRET_KEY = 'foo'

    # PASSWORD_HASHER = 'scrypt'  # or 'bcrypt' or 'pbkdf2'

    # SPHINX_CONFIG = dict(Development.SPHINX_CONFIG)
    # SPHINX_CONFIG['connection_params'] = {'host': '127.0.0.1', 'port': 9306, 'charset': 'utf8'}

    # SPHINX_ROOT = '/path/to/directory/sphinx'
    # SPHINX_SEARCHD = dict(Development.SPHINX_SEARCHD)
    # SPHINX_SEARCHD['listen'] = '0.0.0.0:9306:mysql41'
