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
    #     'charset': 'utf8mb4',
    # }

    # SERVER_NAME = 'example.org'
    # PREFERRED_URL_SCHEME = 'http'

    # LOGLEVEL = logging.DEBUG

    # ADMINS = ['admin@example.org']
    # ERROR_EMAIL_HANDLER_PARAMS = {'mailhost': ('127.0.0.1', 1025)}
    ERROR_EMAIL_FROM = 'minifiction@example.org'

    # EMAIL_HOST = '127.0.0.1'
    # EMAIL_PORT = 1025
    DEFAULT_FROM_EMAIL = 'minifiction@example.org'

    # CAPTCHA_CLASS = 'mini_fiction.captcha.PyCaptcha'  # or:
    # CAPTCHA_CLASS = 'mini_fiction.captcha.ReCaptcha'
    # RECAPTCHA_PUBLIC_KEY = '...'
    # RECAPTCHA_PRIVATE_KEY = '...'

    # CAPTCHA_FOR_GUEST_COMMENTS = True

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

    # Example that allows only english usernames
    # USERNAME_REGEX = r'^[A-Za-z0-9_-]+$'

    # cache - memcached (pip install python-memcached)
    # CACHE_TYPE = 'memcached'
    # CACHE_PARAMS = {
    #     'servers': ['127.0.0.1:11211'],
    #     'key_prefix': 'mfc_',
    # }

    # cache - redis
    # CACHE_TYPE = 'redis'
    # CACHE_PARAMS = {
    #     'host': '127.0.0.1',
    #     'port': 6379,
    #     'password': None,
    #     'db': 0,
    #     'key_prefix': 'mfc_',
    # }

    # cache - filesystem
    # CACHE_TYPE = 'filesystem'
    # CACHE_PARAMS = {
    #     'cache_dir': os.path.join(os.getcwd(), 'cache'),
    # }
