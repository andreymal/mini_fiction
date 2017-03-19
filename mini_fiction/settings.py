#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging


class Config(object):
    LOCALES = {
        # unfinished: 'en': 'English',
        'ru': 'Русский',
    }
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'mnwpNkTYhFeu57Fc9WjVbw7DidbkZoVe'

    PLUGINS = []

    DATABASE_ENGINE = 'sqlite'
    DATABASE = {
        'filename': os.path.join(os.getcwd(), 'db.sqlite3'),
        'create_db': True,
    }
    SQL_DEBUG = False

    JSON_AS_ASCII = False
    MEMCACHE_SERVERS = ['127.0.0.1:11211']
    CACHE_PREFIX = 'mfc_'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    PROXIES_COUNT = 0
    LOGGER_LEVEL = logging.INFO
    LOGGER_STDERR = True

    TEMPLATES_AUTO_RELOAD = False

    ADMINS = []
    ERROR_EMAIL_FROM = 'mini_fiction@localhost.com'
    ERROR_EMAIL_SUBJECT = 'miniFiction error'
    ERROR_EMAIL_HANDLER_PARAMS = {'mailhost': '127.0.0.1'}

    BABEL_DEFAULT_LOCALE = 'ru'
    BABEL_DEFAULT_TIMEZONE = 'Europe/Moscow'

    DEBUG_TB_ENABLED = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PANELS = [
        'flask_debugtoolbar.panels.versions.VersionDebugPanel',
        'flask_debugtoolbar.panels.timer.TimerDebugPanel',
        'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
        'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
        'flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel',
        'flask_debugtoolbar.panels.template.TemplateDebugPanel',
        'mini_fiction.utils.debugtoolbar.PonyDebugPanel',
        'flask_debugtoolbar.panels.logger.LoggingPanel',
        'flask_debugtoolbar.panels.route_list.RouteListDebugPanel',
        'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
    ]
    PONYORM_RECORD_QUERIES = False

    PASSWORD_HASHER = 'pbkdf2'  # or 'bcrypt' or 'scrypt'

    SITE_URL = 'http://localhost:5000'
    SITE_NAME = {
        'default': 'Library',
        'ru': 'Библиотека'
    }
    SITE_FEEDBACK = '/'
    FAVICON_URL = None

    MEDIA_ROOT = os.path.join(os.getcwd(), 'media')
    STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

    LOCALSTATIC_ROOT = None
    LOCALTEMPLATES = None

    SPHINX_DISABLED = False
    SPHINX_CONFIG = {
        'connection_params': {'unix_socket': '/tmp/sphinx_fanfics.socket', 'charset': 'utf8'},
        'excerpts_opts': {'chunk_separator': '…', 'limit': 2048, 'around': 10, 'html_strip_mode': 'strip'},

        'weights_stories': {'title': 100, 'summary': 50, 'notes': 25, 'username': 150},
        'weights_chapters': {'text': 100, 'title': 50, 'notes': 25},

        'limit': 10,
        'select_options': {
            'ranker': 'sph04',
            'max_matches': 1000,
            'retry_count': 5,
            'retry_delay': 1,
            'max_query_time': 10000,  # in milliseconds
        },
    }

    SPHINX_ROOT = os.path.join(os.getcwd(), 'sphinx')
    SPHINX_SEARCHD = {
        'listen': '/tmp/sphinx_fanfics.socket:mysql41',
        'log': '{sphinxroot}/searchd.log',
        'query_log': '{sphinxroot}/query.log',
        'read_timeout': 5,
        'max_children': 20,
        'pid_file': '{sphinxroot}/sphinx.pid',
        'binlog_path': '{sphinxroot}/binlog',
        'workers': 'threads',
    }
    SPHINX_CUSTOM = ''

    COMMENTS_COUNT = {
        'page': 25,
        'main': 5,
        'stream': 50,
        'author_page': 10
    }
    STORIES_COUNT = {'page': 10, 'main': 10, 'stream': 20}
    CHAPTERS_COUNT = {'page': 10, 'main': 10, 'stream': 20}
    COMMENTS_ORPHANS = 5
    COMMENT_MIN_LENGTH = 1
    COMMENT_EDIT_TIME = 15
    BRIEF_COMMENT_LENGTH = 100
    STORY_COMMENTS_BY_GUEST = False
    NOTICE_COMMENTS_BY_GUEST = False
    COMMENT_SPOILER_THRESHOLD = -5
    COMMENTS_TREE_MAXDEPTH = 3

    RSS = {'stories': 20, 'chapters': 20, 'comments': 100}

    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 25
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_SSL = False
    EMAIL_USE_TLS = False
    EMAIL_SSL_KEYFILE = None
    EMAIL_SSL_CERTFILE = None
    DEFAULT_FROM_EMAIL = 'minifiction@localhost.com'

    ACCOUNT_ACTIVATION_DAYS = 5
    REGISTRATION_AUTO_LOGIN = True
    CHECK_PASSWORDS_SECURITY = True

    REGISTRATION_OPEN = True
    AVATARS_UPLOADING = False

    ALLOWED_TAGS = [
        'b', 'i', 'strong', 'em', 's', 'u',
        'p', 'br', 'hr',
        'img', 'a',
        'ul', 'ol', 'li',
        'blockquote', 'sup', 'sub', 'pre', 'small', 'tt'
    ]

    ALLOWED_ATTRIBUTES = {
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'a': ['href', 'rel', 'title', 'target'],
    }

    CHAPTER_ALLOWED_TAGS = [
        'b', 'i', 'strong', 'em', 's', 'u',
        'h3', 'h4', 'h5',
        'p', 'span', 'br', 'hr', 'footnote',
        'img', 'a',
        'ul', 'ol', 'li',
        'blockquote', 'sup', 'sub', 'pre', 'small', 'tt', 'font',
    ]

    CHAPTER_ALLOWED_ATTRIBUTES = {
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'a': ['href', 'rel', 'title', 'target'],
        'span': ['align'],
        'p': ['align'],
        'footnote': ['id'],
        'font': ['size', 'color'],
    }

    PUBLISH_SIZE_LIMIT = 1000
    STARS_MINIMUM_VOTES = 2

    STORY_DOWNLOAD_FORMATS = tuple(reversed((
        'mini_fiction.downloads.fb2.FB2Download',
        'mini_fiction.downloads.html.HTMLDownload',
        # 'mini_fiction.downloads.txt.TXTDownload',
        # 'mini_fiction.downloads.txt.TXT_CP1251Download',
    )))

    CONTACTS = [
        {
            'name': 'website',
            'label': {
                'default': 'Website',
                'ru': 'Вебсайт',
            },
            'schema': {'regex': r'^https?://.+$'},
            'link_template': '{value}',
            'title_template': '{value}',
        },
        {
            'name': 'xmpp',
            'label': {
                'default': 'Jabber ID (XMPP)',
            },
            'schema': {'regex': r'^.+@([^.@][^@]+)'},
            'link_template': 'xmpp:{value}',
            'title_template': '{value}',
        },
        {
            'name': 'skype',
            'label': {
                'default': 'Skype ID',
            },
            'schema': {'regex': r'^[a-zA-Z0-9\._-]+$'},
            'link_template': 'skype:{value}',
            'title_template': '{value}',
        },
    ]

    CELERY_ALWAYS_EAGER = False
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
    CELERY_BROKER_URL = 'redis://localhost:6379/0'

    NSFW_RATING_IDS = (1,)

    RECAPTCHA_USE_SSL = True
    RECAPTCHA_PUBLIC_KEY = ''
    RECAPTCHA_PRIVATE_KEY = ''
    RECAPTCHA_OPTIONS = {'hl': 'ru'}
    NOCAPTCHA = True

    RANDOM_LOGOS = []
    DEFAULT_USERPIC = {'endpoint': 'static', 'filename': 'i/userpic.png'}


class Development(Config):
    DEBUG = True
    SQL_DEBUG = True
    DEBUG_TB_ENABLED = True
    CHECK_PASSWORDS_SECURITY = False
    CELERY_ALWAYS_EAGER = True
    SPHINX_DISABLED = True
    STARS_MINIMUM_VOTES = 1
    PUBLISH_SIZE_LIMIT = 20
    TEMPLATES_AUTO_RELOAD = True


class Test(Config):
    LOCALES = {'ru': 'Русский'}
    DATABASE_ENGINE = 'sqlite'
    DATABASE = {
        'filename': os.path.join(os.getcwd(), 'testdb.sqlite3'),  # ':memory:' breaks with connection pool
        'create_db': True,
    }
    DATABASE_CLEANER = {'provider': 'sqlite3'}  # TODO: MySQL and PostgreSQL
    TESTING = True
    SQL_DEBUG = False
    MEMCACHE_SERVERS = None
    CELERY_ALWAYS_EAGER = True
    SPHINX_DISABLED = True  # TODO: test it
    STARS_MINIMUM_VOTES = 3
    PUBLISH_SIZE_LIMIT = 20
