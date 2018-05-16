#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging

from celery.schedules import crontab


class Config(object):
    LOCALES = {
        # unfinished: 'en': 'English',
        'ru': 'Русский',
    }
    DEBUG = False
    SECRET_KEY = 'mnwpNkTYhFeu57Fc9WjVbw7DidbkZoVe'
    SYSTEM_USER_ID = -1

    USER_AGENT = None  # generated in application.py
    USER_AGENT_POSTFIX = ''

    CHAPTER_LINTER = 'mini_fiction.linters.DefaultChapterLinter'
    PLUGINS = []

    DATABASE_ENGINE = 'sqlite'
    DATABASE = {
        'filename': os.path.join(os.getcwd(), 'db.sqlite3'),
        'create_db': True,
    }
    SQL_DEBUG = False

    # cache config
    CACHE_TYPE = 'memcached'  # 'null', 'redis', 'filesystem'
    CACHE_KEY_PREFIX = 'mfc_'

    # memcached
    CACHE_MEMCACHED_SERVERS = ['127.0.0.1:11211']

    # redis
    CACHE_REDIS_HOST = '127.0.0.1'
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_PASSWORD = None
    CACHE_REDIS_DB = None

    # filesystem
    CACHE_DIR = os.path.join(os.getcwd(), 'cache')

    JSON_AS_ASCII = False
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    PROXIES_COUNT = 0

    TEMPLATES_AUTO_RELOAD = False

    ADMINS = []
    ERROR_EMAIL_FROM = 'mini_fiction@localhost.com'
    ERROR_EMAIL_SUBJECT = 'miniFiction error'
    ERROR_EMAIL_HANDLER_PARAMS = None

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
    PBKDF2_ITERATIONS = 100000

    SERVER_NAME = 'localhost:5000'
    PREFERRED_URL_SCHEME = 'http'
    SITE_NAME = {
        'default': 'Library',
        'ru': 'Библиотека'
    }
    EMAIL_SITE_NAME = None  # SITE_NAME by default
    SITE_INDEX_TITLE = {'default': ''}
    SITE_DESCRIPTION = {'default': ''}
    SITE_FEEDBACK = '/'
    FAVICON_URL = None

    MEDIA_ROOT = os.path.join(os.getcwd(), 'media')

    STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')
    STATIC_VERSION_FILE = 'VERSION'
    STATIC_VERSION_TYPE = 'date'  # or 'hash'
    STATIC_V = None

    LOCALSTATIC_ROOT = None
    LOCALTEMPLATES = None

    SPHINX_DISABLED = False
    SPHINX_CONFIG = {
        'connection_params': {'unix_socket': '/tmp/sphinx_fanfics.socket', 'charset': 'utf8'},
        'excerpts_opts': {'chunk_separator': '…', 'limit': 2048, 'around': 10, 'html_strip_mode': 'strip'},

        'stories_rt_mem_limit': '128M',
        'chapters_rt_mem_limit': '256M',

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
    COMMENT_EDIT_TIME = 15  # minutes
    COMMENT_DELETE_TIME = 2  # minutes
    BRIEF_COMMENT_LENGTH = 175
    STORY_COMMENTS_BY_GUEST = False
    NEWS_COMMENTS_BY_GUEST = False
    COMMENT_SPOILER_THRESHOLD = -5
    COMMENTS_TREE_MAXDEPTH = 4

    RSS = {
        'stories': 20,
        'accounts': 10,
        'chapters': 20,
        'comments': 100,
    }

    EMAIL_HOST = None
    EMAIL_PORT = 25
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_SSL = False
    EMAIL_USE_TLS = False
    EMAIL_SSL_KEYFILE = None
    EMAIL_SSL_CERTFILE = None
    EMAIL_TIMEOUT = 10
    EMAIL_MSGTYPES = {
        'default': 'stories',
        'registration': 'stories_reg',
        'reset_password': 'stories_pwd',
        'change_email': 'stories_chmail',
        'change_email_warning': 'stories_chmail_warn',
    }
    DEFAULT_FROM_EMAIL = ('Библиотека', 'minifiction@localhost.com')
    EMAIL_REDIRECT_TO = None
    EMAIL_DONT_EDIT_SUBJECT_ON_REDIRECT = False

    ACCOUNT_ACTIVATION_DAYS = 5
    REGISTRATION_AUTO_LOGIN = True
    CHECK_PASSWORDS_SECURITY = True

    REGISTRATION_OPEN = True
    AVATARS_UPLOADING = False

    STORY_NOTIFICATIONS_INTERVAL = 3600

    WTF_CSRF_TIME_LIMIT = 3600 * 24 * 7  # 1 week

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

    PREMODERATION = True
    PUBLISH_SIZE_LIMIT = 400  # words
    MAX_SIZE_FOR_DIFF = 75000  # chars
    DIFF_CONTEXT_SIZE = 150  # chars

    STORY_VOTING_CLASS = 'mini_fiction.story_voting.star.StarVoting'
    VOTING_MAX_VALUE = 5
    MINIMUM_VOTES_FOR_VIEW = 5
    VOTES_MID = 4.1

    STORY_COMMENTS_MODE = 'pub'  # or 'on' or 'off' or 'nodraft'
    STORY_DIRECT_ACCESS = 'none'  # or 'all' or 'nodraft' or 'anodraft'
    STORY_DIRECT_ACCESS_FOR_GUEST = False  # always True for 'anodraft'

    STORY_DOWNLOAD_FORMATS = tuple(reversed((
        'mini_fiction.downloads.fb2.FB2Download',
        # 'mini_fiction.downloads.fb2.FB2ZipDownload',
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
        {
            'name': 'telegram',
            'label': {
                'default': 'Telegram',
            },
            'schema': {'regex': r'^[a-zA-Z0-9\._-]+$'},
            'link_template': 'https://t.me/{value}',
            'title_template': '{value}',
        },
        {
            'name': 'vk',
            'label': {
                'default': 'VK login',
                'ru': 'Логин ВКонтакте',
            },
            'schema': {'regex': r'^[a-zA-Z0-9\._-]+$'},
            'link_template': 'https://vk.com/{value}',
            'title_template': '{value}',
        },
    ]

    CELERY_CONFIG = {
        'broker_url': 'redis://localhost:6379/0',
        'task_always_eager': False,
        'task_serializer': 'json',
        'accept_content': {'json', 'msgpack', 'yaml'},
        'timezone': 'UTC',
        'beat_schedule': {
            'daily_zip_dump': {
                'task': 'zip_dump',
                'schedule': crontab(hour=2, minute=0),
            }
        }
    }

    ZIP_DUMP_PATH = 'mini_fiction_dump.zip'  # relative to /media/
    ZIP_TMP_DUMP_PATH = None  # default ZIP_DUMP_PATH + '.tmp'

    CAPTCHA_CLASS = None
    CAPTCHA_FOR_GUEST_COMMENTS = False

    # PyCaptcha config
    PYCAPTCHA_FONTS = [
        os.path.join(os.path.dirname(__file__), 'static', 'fonts', 'PTC75F.ttf'),
    ]
    PYCAPTCHA_CACHE_PREFIX = 'pycaptcha_'
    PYCAPTCHA_CHARS = 'ABCDEFGHJKLMNPQRSTUWXYZ23456789'
    PYCAPTCHA_CASE_SENSITIVE = False
    PYCAPTCHA_LENGTH = 7

    # ReCaptcha config
    RECAPTCHA_USE_SSL = True
    RECAPTCHA_PUBLIC_KEY = ''
    RECAPTCHA_PRIVATE_KEY = ''
    RECAPTCHA_OPTIONS = {'hl': 'ru'}

    DEFAULT_USERPIC = {'endpoint': 'static', 'filename': 'i/userpic.png'}
    LOADING_ICON = {'endpoint': 'static', 'filename': 'i/ajax-loader.gif'}

    # Sitemap
    SITEMAP_STORIES_PER_FILE = 1000
    SITEMAP_PING_URLS = []  # ['http://google.com/ping?sitemap={url}', ...]

    # Testing
    TESTING = False
    SELENIUM_HEADLESS = True


class Development(Config):
    DEBUG = True
    SQL_DEBUG = True
    CHECK_PASSWORDS_SECURITY = False
    SPHINX_DISABLED = True
    MINIMUM_VOTES_FOR_VIEW = 1
    PUBLISH_SIZE_LIMIT = 20
    TEMPLATES_AUTO_RELOAD = True
    CELERY_CONFIG = dict(Config.CELERY_CONFIG)
    CELERY_CONFIG['task_always_eager'] = True


class Test(Config):
    LOCALES = {'ru': 'Русский'}
    DATABASE_ENGINE = 'sqlite'
    DATABASE = {
        'filename': os.path.join(os.getcwd(), 'testmedia', 'testdb.sqlite3'),  # ':memory:' breaks with connection pool
        'create_db': True,
    }
    DATABASE_CLEANER = {'provider': 'sqlite3'}  # TODO: MySQL and PostgreSQL
    TESTING = True
    TESTING_DIRECTORY = os.path.join(os.getcwd(), 'testmedia')
    MEDIA_ROOT = os.path.join(os.getcwd(), 'testmedia', 'media')
    SQL_DEBUG = False
    CACHE_TYPE = 'null'
    SPHINX_DISABLED = True  # TODO: test it
    MINIMUM_VOTES_FOR_VIEW = 3
    PUBLISH_SIZE_LIMIT = 20
    CELERY_CONFIG = dict(Config.CELERY_CONFIG)
    CELERY_CONFIG['task_always_eager'] = True
