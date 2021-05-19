import os
import logging
from typing import Optional, TypedDict

from celery.schedules import crontab
from flask_babel import lazy_gettext


class RedisConf(TypedDict):
    host: str
    port: int
    db: int


class Config(object):
    LOCALES = {
        # unfinished: 'en': 'English',
        'ru': 'Русский',
    }
    SECRET_KEY = 'mnwpNkTYhFeu57Fc9WjVbw7DidbkZoVe'
    SYSTEM_USER_ID = -1

    USER_AGENT = None  # generated in application.py
    USER_AGENT_POSTFIX = ''

    CHAPTER_LINTER = 'mini_fiction.linters.DefaultChapterLinter'
    PLUGINS = []

    # Required for Pony ORM when FLASK_ENV=development
    PRESERVE_CONTEXT_ON_EXCEPTION = False

    # logging
    LOGLEVEL = logging.INFO
    LOGFORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
    ERROR_LOGFORMAT = 'IP: %(remote_addr)s\nUser: %(username)s (%(user_id)s)\n\n%(message)s'
    AUTH_LOG = True
    AUTH_CAPTCHA_MIN_TRIES = 5
    AUTH_CAPTCHA_TIMEOUT = 600

    # database
    DATABASE_ENGINE = 'sqlite'
    DATABASE = {
        'filename': os.path.join(os.getcwd(), 'db.sqlite3'),
        'create_db': True,
    }
    SQL_DEBUG = False

    # cache config
    CACHE_TYPE = 'null'  # 'memcached', 'redis', 'filesystem', 'uwsgi', 'simple'
    CACHE_PARAMS = {}

    # Rate limiter
    RATE_LIMIT_BACKEND: Optional[RedisConf] = None
    RATE_LIMIT_PREFIX = 'mf_rate_limit_'

    RATE_LIMITS = {
        # max 10 comments per 6 hours
        'comment_newuser': (10, 3600 * 6),
        # max 20 comments per hour
        'comment': (20, 3600),
        # max 30 comments per hour from single ip
        'comment_ip': (30, 3600),
        # max 5 comment votes per hour
        'comment_vote_plus': (5, 3600),
        'comment_vote_minus': (5, 3600),
        # max 5 stories per day
        'story': (5, 3600 * 24),
        # max 100 chapters per hour
        'chapter': (100, 3600),
    }

    EVENT_BUS: Optional[RedisConf] = None

    CHAPTER_NEW_HTML_BACKEND_CACHE_TIME = 3600 * 12  # seconds
    CHAPTER_OLD_HTML_BACKEND_CACHE_TIME = 1800  # seconds
    CHAPTER_NEW_AGE = 3600 * 24 * 7  # seconds
    CHAPTER_HTML_FRONTEND_CACHE_TIME = 600  # seconds

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

    DEFAULT_DATE_FORMAT = 'd MMMM y'
    DEFAULT_DATETIME_FORMAT = 'd MMMM y, HH:mm'
    DEFAULT_TIME_FORMAT = 'HH:mm'

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

    USERNAME_REGEX = r'^[0-9a-zA-Zа-яА-ЯёЁ_@+-\. ]+$'
    USERNAME_HELP = 'Только русские/латинские буквы, цифры, пробел, точка и символы _ @ + -'
    USERNAME_ERROR_MESSAGE = (
        'Пожалуйста, исправьте ошибку в логине - он может содержать только '
        'русские/латинские буквы, цифры, пробел, точку и символы _ @ + -'
    )
    PASSWORD_HASHER = 'pbkdf2'  # or 'bcrypt' or 'scrypt'
    PBKDF2_ITERATIONS = 200000

    NORMALIZED_TAGS_WHITELIST = (
        '_-()×°'
        '0123456789'
        'abcdefghijklmnopqrstuvwxyz'
        'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿß'
        'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        'ґєії'
    )
    NORMALIZED_TAGS_DELIMETERS = (
        ' \u00a0/\\—–[]<>:;?!%&@*+=«»|'
    )
    TAGS_BLACKLIST_REGEX = {
        r'^[_\-()×°]+$': lazy_gettext('Empty tag'),
    }

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
    SESSION_COOKIE_DOMAIN = False

    # used by the converter to replace absolute links to relative
    # Example: SERVER_NAME_REGEX = r'(www\.)?example\.org|oldsite\.(ru|org|info)'
    SERVER_NAME_REGEX = r'localhost:5000'

    # Static files configuration

    STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')
    STATIC_URL = '/static'
    STATIC_VERSION_FILE = 'VERSION'
    STATIC_VERSION_TYPE = 'date'  # or 'hash'
    STATIC_V = None

    LOCALSTATIC_ROOT = None
    LOCALSTATIC_URL = '/localstatic'

    MEDIA_ROOT = os.path.join(os.getcwd(), 'media')
    MEDIA_URL = '/media'

    FRONTEND_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), 'static/build/manifest.json')
    FRONTEND_MANIFEST_AUTO_RELOAD = False

    # [{"endpoint": "localstatic", filename="your/local/file"}]
    EXTRA_CSS = []
    EXTRA_JS = []

    LOCALTEMPLATES = None

    SPHINX_DISABLED = False
    SPHINX_ROOT = os.path.join(os.getcwd(), 'sphinx')
    SPHINX_CONFIG = {
        'connection_params': {'unix_socket': '/tmp/sphinx_fanfics.socket', 'charset': 'utf8mb4'},
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

    SPHINX_INDEX_OPTIONS = {
        'morphology': 'stem_enru',
        # Recommended: 'morphology': 'lemmatize_ru_all, lemmatize_en_all',
        'min_word_len': 2,
        'min_infix_len': 3,
        'index_exact_words': 1,
        'wordforms': None,
        'exceptions': None,
        'expand_keywords': 1,
    }

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
    SPHINX_COMMON = {
        # 'lemmatizer_base': '/path/to/dicts'
    }
    SPHINX_CUSTOM = ''

    COMMENTS_COUNT = {
        'page': 25,
        'main': 5,
        'stream': 50,
        'author_page': 10
    }
    STORIES_COUNT = {'stream': 20, 'tags': 20, 'lists': 20}
    CHAPTERS_COUNT = {'main': 10, 'stream': 20}
    COMMENTS_ORPHANS = 5
    COMMENT_MIN_LENGTH = 1
    COMMENT_EDIT_TIME = 15  # minutes
    COMMENT_DELETE_TIME = 2  # minutes
    BRIEF_COMMENT_LENGTH = 175
    STORY_COMMENTS_BY_GUEST = False
    NEWS_COMMENTS_BY_GUEST = False
    COMMENT_SPOILER_THRESHOLD = -5
    COMMENTS_TREE_MAXDEPTH = 4

    CHAPTER_MAX_LENGTH = 500000

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
        'strong', 'em', 's', 'u',
        'p', 'span', 'br', 'hr',
        'img', 'a',
        'ul', 'ol', 'li',
        'blockquote', 'sup', 'sub', 'pre', 'small'
    ]

    ALLOWED_ATTRIBUTES = {
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'a': ['href', 'rel', 'title', 'target'],
        'span': {
            'class': ['spoiler-gray'],
        },
    }

    CHAPTER_ALLOWED_TAGS = [
        'strong', 'em', 's', 'u',
        'h3',
        'p', 'span', 'br', 'hr', 'footnote',
        'img', 'a',
        'ul', 'ol', 'li',
        'blockquote', 'sup', 'sub', 'pre', 'small', 'font',
    ]

    CHAPTER_ALLOWED_ATTRIBUTES = {
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'a': ['href', 'rel', 'title', 'target'],
        'span': {
            'align': ['left', 'center', 'right'],
        },
        'p': {
            'align': ['left', 'center', 'right'],
        },
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
    STORY_DIRECT_ACCESS = 'none'  # or 'all' or 'allguest' or 'nodraft' or 'anodraft'
    STORY_DIRECT_ACCESS_FOR_GUEST = False  # always True for 'anodraft'

    UMASK = 0o022

    STORY_DOWNLOAD_FORMATS = tuple(reversed((
        'mini_fiction.downloads.fb2.FB2Download',
        # 'mini_fiction.downloads.fb2.FB2ZipDownload',
        'mini_fiction.downloads.html.HTMLDownload',
        # 'mini_fiction.downloads.txt.TXTDownload',
        # 'mini_fiction.downloads.txt.TXT_CP1251Download',
    )))

    STORY_DOWNLOAD_SLUGIFY_FILENAMES = False

    ACCEL_REDIRECT_HEADER = None  # set 'X-Accel-Redirect' if you use nginx

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

    # Sitemap
    SITEMAP_STORIES_PER_FILE = 1000
    SITEMAP_PING_URLS = []  # ['http://google.com/ping?sitemap={url}', ...]

    # Index sidebar
    INDEX_SIDEBAR = {
        'chapters_updates': 'mini_fiction.views.sidebar.chapters_updates',
        'comments_updates': 'mini_fiction.views.sidebar.comments_updates',
        'news': 'mini_fiction.views.sidebar.news',
    }
    INDEX_SIDEBAR_ORDER = [
        'chapters_updates',
        'comments_updates',
        'news',
    ]

    # Testing
    TESTING = False
    SELENIUM_HEADLESS = True


class Development(Config):
    SQL_DEBUG = True
    CHECK_PASSWORDS_SECURITY = False
    SPHINX_DISABLED = True
    MINIMUM_VOTES_FOR_VIEW = 1
    PUBLISH_SIZE_LIMIT = 20
    TEMPLATES_AUTO_RELOAD = True
    CELERY_CONFIG = dict(Config.CELERY_CONFIG)
    CELERY_CONFIG['task_always_eager'] = True
    FRONTEND_MANIFEST_AUTO_RELOAD = True


class Test(Config):
    TESTING = True
    LOCALES = {'ru': 'Русский'}
    DATABASE_ENGINE = 'sqlite'
    DATABASE = {
        'filename': os.path.join(os.getcwd(), 'testmedia', 'testdb.sqlite3'),  # ':memory:' breaks with connection pool
        'create_db': True,
    }
    DATABASE_CLEANER = {'provider': 'sqlite3'}  # TODO: MySQL and PostgreSQL
    TESTING_DIRECTORY = os.path.join(os.getcwd(), 'testmedia')
    MEDIA_ROOT = os.path.join(os.getcwd(), 'testmedia', 'media')
    SQL_DEBUG = False
    CACHE_TYPE = 'null'
    SPHINX_DISABLED = True  # TODO: test it
    MINIMUM_VOTES_FOR_VIEW = 3
    PUBLISH_SIZE_LIMIT = 20
    CELERY_CONFIG = dict(Config.CELERY_CONFIG)
    CELERY_CONFIG['task_always_eager'] = True
